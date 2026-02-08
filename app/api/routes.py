"""FastAPI routes."""
import uuid
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.memory import MemorySaver
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ApprovalRequest,
    ApprovalResponse,
    ConversationHistoryResponse,
    ConversationHistoryItem,
    ConversationListResponse,
    ConversationListItem,
    DelayedOrderResponse,
    OrderListResponse,
    OrderListItem,
)
from app.api.approval_mapping import approval_to_conversation
from app.models.database import get_db, AsyncSessionLocal
from app.approvals.service import ApprovalService
from app.conversations.service import ConversationService
from app.graph.graph import build_agent_graph
from app.graph.state import AgentState

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared checkpointer for all conversations (in production, use Redis or database)
# Each conversation is differentiated by thread_id in the config
_shared_checkpointer = MemorySaver()
_graph_instance = None  # Single graph instance for all conversations


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Handle chat request and invoke LangGraph agent.
    
    Args:
        request: Chat request
        db: Database session
        
    Returns:
        Chat response
    """
    logger.info("=" * 80)
    logger.info("CHAT API REQUEST RECEIVED")
    logger.info(f"Message: {request.message}")
    logger.info(f"Conversation ID: {request.conversation_id}")
    logger.info("=" * 80)
    
    try:
        # Initialize approval service
        logger.info("Initializing ApprovalService...")
        approval_service = ApprovalService(db)
        logger.info("ApprovalService initialized successfully")
        
        # Build or get graph (single instance for all conversations)
        global _graph_instance
        if _graph_instance is None:
            logger.info("Building graph instance (shared across all conversations)...")
            _graph_instance = build_agent_graph(approval_service, checkpointer=_shared_checkpointer)
            logger.info("Graph instance created successfully")
        else:
            logger.info("Using existing shared graph instance")
        
        graph = _graph_instance
        
        # Get conversation_id for thread_id
        conversation_id = request.conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
        logger.info(f"Using conversation_id (thread_id): {conversation_id}")
        
        # Create config for checkpointing
        config = {"configurable": {"thread_id": conversation_id}}
        logger.info(f"Checkpoint config: {config}")
        
        # Load previous state from checkpoint if it exists
        conversation_history = []
        previous_state = None
        
        try:
            # Try to get the latest checkpoint state for this thread_id
            from langgraph.checkpoint.base import Checkpoint
            checkpoint_list = _shared_checkpointer.list(config, limit=1)
            if checkpoint_list:
                checkpoint_id = checkpoint_list[0].get("checkpoint_id")
                if checkpoint_id:
                    checkpoint_data = _shared_checkpointer.get(config, checkpoint_id)
                    if checkpoint_data and checkpoint_data.get("channel_values"):
                        previous_state = checkpoint_data["channel_values"]
                        conversation_history = previous_state.get("conversation_history", [])
                        logger.info(f"Loaded conversation_history from checkpoint: {len(conversation_history)} messages")
        except Exception as e:
            logger.warning(f"Could not load previous state from checkpoint: {str(e)}")
            conversation_history = []
        
        # Prepare initial state - use loaded conversation_history
        logger.info("Preparing initial state...")
        initial_state: AgentState = {
            "user_message": request.message,  # New message for this request
            "conversation_history": conversation_history,  # Loaded from checkpoint
            "order_data": None,  # Reset for new request
            "policy_context": None,  # Reset for new request
            "agent_decision": None,  # Reset for new request
            "approval_id": None,  # Reset for new request
            "approval_status": None,  # Reset for new request
            "execution_result": None,  # Reset for new request
            "confidence": 0.0,  # Reset for new request
            "iteration_count": 0,  # Reset for new request
            "next_step": "NONE",  # Reset for new request
            "final_response": None,  # Reset for new request
            "_conversation_id": conversation_id,
        }
        
        logger.info(f"Initial state prepared: user_message='{request.message}', conversation_history={len(conversation_history)} messages")
        logger.info(f"Initial state _conversation_id: {initial_state.get('_conversation_id')}")
        
        # Invoke graph
        logger.info("Starting graph execution...")
        result = None
        event_count = 0
        async for event in graph.astream(
            initial_state,
            config=config,
            stream_mode="values",
        ):
            event_count += 1
            logger.info(f"Graph event #{event_count} received")
            logger.debug(f"Event state keys: {list(event.keys()) if event else 'None'}")
            logger.debug(f"Event next_step: {event.get('next_step') if event else 'None'}")
            logger.debug(f"Event final_response: {event.get('final_response') if event else 'None'}")
            logger.debug(f"Event agent_decision: {event.get('agent_decision') if event else 'None'}")
            result = event
        
        logger.info(f"Graph execution completed. Total events: {event_count}")
        
        if not result:
            logger.error("Graph execution returned no result!")
            raise HTTPException(status_code=500, detail="Agent execution failed")
        
        logger.info("Graph execution result received")
        logger.info(f"Result keys: {list(result.keys())}")
        logger.info(f"Result final_response: {result.get('final_response')}")
        logger.info(f"Result approval_id: {result.get('approval_id')}")
        logger.info(f"Result agent_decision: {result.get('agent_decision')}")
        logger.info(f"Result next_step: {result.get('next_step')}")
        logger.info(f"Result iteration_count: {result.get('iteration_count')}")
        
        # Check if approval is required
        approval_id = result.get("approval_id")
        requires_approval = approval_id is not None
        logger.info(f"Approval required: {requires_approval}, approval_id: {approval_id}")
        
        # Get final response
        # 
        # IMPORTANT: Fallback logic for interrupted graph execution
        # 
        # Normal flow: format_final_response node sets final_response in state
        # However, with interrupt_after=["human_approval"], the graph can be interrupted
        # AFTER human_approval runs but BEFORE format_final_response runs.
        # 
        # In this scenario:
        # 1. llm_reasoning node creates agent_decision with final_answer field
        # 2. human_approval node runs and graph interrupts (waiting for approval)
        # 3. format_final_response node hasn't run yet, so final_response is None
        # 4. But agent_decision.final_answer already contains the LLM's response
        # 
        # Solution: Use agent_decision.final_answer as fallback when final_response is missing
        # This ensures we always return a meaningful response to the user, even when
        # the graph execution is interrupted before reaching format_final_response.
        #
        # Example scenario:
        # - User: "Cancel order ORD-12345"
        # - Flow: llm_reasoning → output_guardrails → human_approval → [INTERRUPT]
        # - format_final_response never runs, but agent_decision.final_answer has the answer
        final_response = result.get("final_response")
        if not final_response:
            # Fallback: Extract response from agent_decision if format_final_response didn't run
            agent_decision = result.get("agent_decision")
            if agent_decision and isinstance(agent_decision, dict):
                final_response = agent_decision.get("final_answer")
        
        # Final fallback: Use default error message if no response found anywhere
        if not final_response:
            final_response = "I apologize, but I couldn't process your request."
        
        logger.info(f"Final response: {final_response}")
        
        if not final_response or final_response == "I apologize, but I couldn't process your request.":
            logger.warning("Final response is empty or default fallback!")
            logger.warning(f"Full result state: {result}")
        
        # Register or update conversation in database
        try:
            conversation_service = ConversationService(db)
            # Use first message as title if it's a new conversation
            title = None
            if len(conversation_history) == 0:
                title = request.message[:50]  # Use first 50 chars as title
            
            # Update conversation with last message
            await conversation_service.get_or_create_conversation(
                conversation_id=conversation_id,
                title=title,
                last_message=request.message[:500],  # Truncate to 500 chars
            )
            logger.info(f"Conversation {conversation_id} registered/updated in database")
        except Exception as e:
            logger.warning(f"Failed to register conversation: {str(e)}")
            # Don't fail the request if conversation registration fails
        
        response = ChatResponse(
            response=final_response,
            requires_approval=requires_approval,
            approval_id=approval_id,
        )
        
        logger.info("=" * 80)
        logger.info("CHAT API RESPONSE")
        logger.info(f"Response: {response.response[:100]}..." if len(response.response) > 100 else f"Response: {response.response}")
        logger.info(f"Requires approval: {response.requires_approval}")
        logger.info(f"Approval ID: {response.approval_id}")
        logger.info("=" * 80)
        
        return response
        
    except HTTPException:
        logger.error("HTTPException raised", exc_info=True)
        raise
    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERROR IN CHAT API")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@router.post("/approvals/{approval_id}", response_model=ApprovalResponse)
async def approve_action(
    approval_id: str,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """
    Approve or reject an action and resume agent execution.
    
    Args:
        approval_id: Approval ID
        request: Approval request
        db: Database session
        
    Returns:
        Approval response
    """
    logger.info("=" * 80)
    logger.info("APPROVAL API REQUEST RECEIVED")
    logger.info(f"Approval ID: {approval_id}")
    logger.info(f"Status: {request.status}")
    logger.info("=" * 80)
    
    try:
        from app.models.domain import ApprovalStatus
        
        # Validate status
        if request.status.upper() not in ["APPROVED", "REJECTED"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be APPROVED or REJECTED"
            )
        
        # Get approval service and check current status
        approval_service = ApprovalService(db)
        status = ApprovalStatus.APPROVED if request.status.upper() == "APPROVED" else ApprovalStatus.REJECTED
        
        # Get current approval status before updating
        logger.info(f"Fetching current approval status for {approval_id}...")
        current_approval = await approval_service.get_approval(approval_id)
        if not current_approval:
            logger.error(f"Approval {approval_id} not found")
            raise HTTPException(status_code=404, detail="Approval not found")
        
        logger.info(f"Current approval status: {current_approval.status.value}")
        
        # Prevent updating if approval is already processed
        if current_approval.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
            logger.warning(f"Approval {approval_id} is already {current_approval.status.value.lower()}")
            raise HTTPException(
                status_code=400,
                detail=f"Approval {approval_id} is already {current_approval.status.value.lower()}. Cannot update an already processed approval."
            )
        
        # Update approval (only if still PENDING)
        logger.info(f"Updating approval {approval_id} to status: {status.value}")
        approval = await approval_service.update_approval(
            approval_id=approval_id,
            status=status,
        )
        logger.info(f"Approval updated successfully")
        
        # Find conversation that has this approval
        conversation_id = approval_to_conversation.get(approval_id)
        logger.info(f"Conversation ID for approval: {conversation_id}")
        
        if not conversation_id:
            logger.warning(f"No conversation_id mapping found for approval {approval_id}")
            # If mapping not found, return response without resuming
            # (This can happen if the mapping was lost or approval was created differently)
            message = (
                f"Action {approval.action} for order {approval.order_id} has been {status.value.lower()}."
            )
            return ApprovalResponse(
                status=status.value.lower(),
                message=message,
            )
        
        # Use the shared graph instance
        global _graph_instance
        if _graph_instance is None:
            logger.error("Graph instance is None!")
            raise HTTPException(
                status_code=500,
                detail="Graph instance not initialized"
            )
        
        graph = _graph_instance
        config = {"configurable": {"thread_id": conversation_id}}
        logger.info(f"Resuming graph with config: {config}")
        
        # Resume graph execution (pass None to continue from checkpoint)
        # Use ainvoke to run graph to completion instead of astream
        result = None
        try:
            logger.info("Starting graph resumption...")
            result = await graph.ainvoke(
                None,  # None means continue from checkpoint
                config=config,
            )
            logger.info("Graph resumption completed via ainvoke")
            logger.debug(f"Result state keys: {list(result.keys()) if result else 'None'}")
            logger.debug(f"Result next_step: {result.get('next_step') if result else 'None'}")
            logger.debug(f"Result approval_status: {result.get('approval_status') if result else 'None'}")
            logger.debug(f"Result execution_result: {'present' if result.get('execution_result') else 'None'}")
            logger.debug(f"Result final_response: {'present' if result.get('final_response') else 'None'}")
        except Exception as e:
            logger.error(f"Error resuming graph: {str(e)}", exc_info=True)
            # If resume fails, still return approval response
            message = (
                f"Action {approval.action} for order {approval.order_id} has been {status.value.lower()}, "
                f"but failed to resume graph: {str(e)}"
            )
            return ApprovalResponse(
                status=status.value.lower(),
                message=message,
            )
        
        # Build response message
        logger.info(f"Building response - result is {'present' if result else 'None'}")
        if result:
            final_response = result.get("final_response", "")
            execution_result = result.get("execution_result")
            
            logger.info(f"Final response: {'present' if final_response else 'empty'}")
            logger.info(f"Execution result: {'present' if execution_result else 'None'}")
            if execution_result:
                logger.info(f"Execution success: {execution_result.get('success')}")
                logger.info(f"Execution message: {execution_result.get('message', 'N/A')}")
                if not execution_result.get('success'):
                    logger.warning(f"Execution error: {execution_result.get('error', 'N/A')}")
            
            message = (
                f"Action {approval.action} for order {approval.order_id} has been {status.value.lower()}."
            )
            
            # Only add execution result message, not the LLM's final_answer (which contains apology text)
            if execution_result and execution_result.get("success"):
                # Use only the execution result message, not the full final_response
                message += f" {execution_result.get('message', 'Action executed successfully.')}"
            elif execution_result and not execution_result.get("success"):
                # If execution failed, add error
                message += f" Note: {execution_result.get('error', 'Action execution failed.')}"
        else:
            logger.warning("Result is None - graph may not have resumed properly")
            message = (
                f"Action {approval.action} for order {approval.order_id} has been {status.value.lower()}."
            )
        
        logger.info("=" * 80)
        logger.info("APPROVAL API RESPONSE")
        logger.info(f"Status: {status.value.lower()}")
        logger.info(f"Message: {message}")
        logger.info("=" * 80)
        
        return ApprovalResponse(
            status=status.value.lower(),
            message=message,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERROR IN APPROVAL API")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"Error processing approval: {str(e)}")


@router.get("/conversations/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: str,
) -> ConversationHistoryResponse:
    """
    Get conversation history for a given conversation ID.
    
    Args:
        conversation_id: Conversation ID (thread_id)
        
    Returns:
        Conversation history response
    """
    logger.info("=" * 80)
    logger.info("CONVERSATION HISTORY API REQUEST RECEIVED")
    logger.info(f"Conversation ID: {conversation_id}")
    logger.info("=" * 80)
    
    try:
        # Create config for checkpointing
        config = {"configurable": {"thread_id": conversation_id}}
        
        # Try to get the latest checkpoint state for this thread_id
        conversation_history = []
        
        try:
            from langgraph.checkpoint.base import Checkpoint
            checkpoint_list = _shared_checkpointer.list(config, limit=1)
            if checkpoint_list:
                checkpoint_id = checkpoint_list[0].get("checkpoint_id")
                if checkpoint_id:
                    checkpoint_data = _shared_checkpointer.get(config, checkpoint_id)
                    if checkpoint_data and checkpoint_data.get("channel_values"):
                        previous_state = checkpoint_data["channel_values"]
                        conversation_history = previous_state.get("conversation_history", [])
                        logger.info(f"Loaded conversation_history from checkpoint: {len(conversation_history)} messages")
        except Exception as e:
            logger.warning(f"Could not load conversation history from checkpoint: {str(e)}")
            conversation_history = []
        
        # Convert conversation history to response format
        history_items = [
            ConversationHistoryItem(role=msg.get("role", "unknown"), content=msg.get("content", ""))
            for msg in conversation_history
        ]
        
        logger.info(f"Returning {len(history_items)} messages for conversation {conversation_id}")
        logger.info("=" * 80)
        
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=history_items,
        )
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERROR IN CONVERSATION HISTORY API")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"Error fetching conversation history: {str(e)}")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> ConversationListResponse:
    """
    Get list of all conversations.
    
    Args:
        db: Database session
        limit: Maximum number of conversations to return (default: 100)
        offset: Number of conversations to skip (default: 0)
        
    Returns:
        Conversation list response
    """
    logger.info("=" * 80)
    logger.info("CONVERSATION LIST API REQUEST RECEIVED")
    logger.info(f"Limit: {limit}, Offset: {offset}")
    logger.info("=" * 80)
    
    try:
        conversation_service = ConversationService(db)
        conversations = await conversation_service.list_conversations(limit=limit, offset=offset)
        
        # Convert to response format
        conversation_items = [
            ConversationListItem(
                conversation_id=conv.conversation_id,
                title=conv.title,
                last_message=conv.last_message,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
            )
            for conv in conversations
        ]
        
        logger.info(f"Returning {len(conversation_items)} conversations")
        logger.info("=" * 80)
        
        return ConversationListResponse(conversations=conversation_items)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERROR IN CONVERSATION LIST API")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"Error fetching conversation list: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a conversation.
    
    Args:
        conversation_id: Conversation ID
        db: Database session
        
    Returns:
        Success message
    """
    logger.info("=" * 80)
    logger.info("DELETE CONVERSATION API REQUEST RECEIVED")
    logger.info(f"Conversation ID: {conversation_id}")
    logger.info("=" * 80)
    
    try:
        conversation_service = ConversationService(db)
        deleted = await conversation_service.delete_conversation(conversation_id)
        
        if not deleted:
            logger.warning(f"Conversation {conversation_id} not found")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        logger.info(f"Conversation {conversation_id} deleted successfully")
        logger.info("=" * 80)
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERROR IN DELETE CONVERSATION API")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")


@router.post("/orders/create-delayed", response_model=DelayedOrderResponse)
async def create_delayed_order(
    db: AsyncSession = Depends(get_db),
) -> DelayedOrderResponse:
    """
    Create a mock delayed order in the database.
    
    A delayed order is one where the expected_delivery_date is in the past,
    making it eligible for delayed order policies.
    
    Args:
        db: Database session
        
    Returns:
        Delayed order creation response with order_id
    """
    logger.info("=" * 80)
    logger.info("CREATE DELAYED ORDER API REQUEST RECEIVED")
    logger.info("=" * 80)
    
    try:
        from datetime import date, timedelta
        import uuid
        from app.models.domain import Order, OrderStatus
        from app.actions.order_repository import OrderRepository
        
        # Generate a unique order ID
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Create a delayed order (expected_delivery_date is 10 days ago)
        delayed_order = Order(
            order_id=order_id,
            status=OrderStatus.PLACED,  # Order is placed but not delivered
            expected_delivery_date=date.today() - timedelta(days=10),  # 10 days delayed
            amount=199.99,
            refundable=True,
        )
        
        # Create order in database using the provided session
        repository = OrderRepository(db)
        
        # Check if order already exists (unlikely but safe)
        exists = await repository.order_exists(order_id)
        if exists:
            # If exists, generate a new ID
            order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            delayed_order.order_id = order_id
        
        # Create the order
        created_order = await repository.create_order(delayed_order)
        logger.info(f"Delayed order created successfully - order_id: {created_order.order_id}")
        
        logger.info("=" * 80)
        logger.info("CREATE DELAYED ORDER API RESPONSE")
        logger.info(f"Order ID: {order_id}")
        logger.info("=" * 80)
        
        return DelayedOrderResponse(
            order_id=order_id,
            message=f"Mock delayed order created successfully. Order ID: {order_id}",
        )
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERROR IN CREATE DELAYED ORDER API")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"Error creating delayed order: {str(e)}")


@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> OrderListResponse:
    """
    Get list of all orders.
    
    Args:
        db: Database session
        limit: Maximum number of orders to return (default: 100)
        offset: Number of orders to skip (default: 0)
        
    Returns:
        Order list response
    """
    logger.info("=" * 80)
    logger.info("ORDER LIST API REQUEST RECEIVED")
    logger.info(f"Limit: {limit}, Offset: {offset}")
    logger.info("=" * 80)
    
    try:
        from sqlalchemy import func, select, desc
        from app.models.database import OrderDB
        
        # Get total count for pagination
        count_stmt = select(func.count(OrderDB.order_id))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Fetch orders with timestamps from database
        stmt = (
            select(OrderDB)
            .order_by(desc(OrderDB.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        orders_db = result.scalars().all()
        
        # Convert to response format
        order_items = [
            OrderListItem(
                order_id=order_db.order_id,
                status=order_db.status.value,
                expected_delivery_date=order_db.expected_delivery_date.isoformat(),
                amount=order_db.amount,
                refundable=order_db.refundable,
                description=order_db.description,
                created_at=order_db.created_at.isoformat(),
                updated_at=order_db.updated_at.isoformat(),
            )
            for order_db in orders_db
        ]
        
        logger.info(f"Returning {len(order_items)} orders (total: {total})")
        logger.info("=" * 80)
        
        return OrderListResponse(orders=order_items, total=total)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERROR IN ORDER LIST API")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full exception:", exc_info=True)
        logger.error("=" * 80)
        raise HTTPException(status_code=500, detail=f"Error fetching order list: {str(e)}")

