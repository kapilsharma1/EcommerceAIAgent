"""FastAPI routes."""
import uuid
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.memory import MemorySaver
from app.api.schemas import ChatRequest, ChatResponse, ApprovalRequest, ApprovalResponse
from app.api.approval_mapping import approval_to_conversation
from app.models.database import get_db
from app.approvals.service import ApprovalService
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
        current_approval = await approval_service.get_approval(approval_id)
        if not current_approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        
        # Prevent updating if approval is already processed
        if current_approval.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
            raise HTTPException(
                status_code=400,
                detail=f"Approval {approval_id} is already {current_approval.status.value.lower()}. Cannot update an already processed approval."
            )
        
        # Update approval (only if still PENDING)
        approval = await approval_service.update_approval(
            approval_id=approval_id,
            status=status,
        )
        
        # Find conversation that has this approval
        conversation_id = approval_to_conversation.get(approval_id)
        
        if not conversation_id:
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
            raise HTTPException(
                status_code=500,
                detail="Graph instance not initialized"
            )
        
        graph = _graph_instance
        config = {"configurable": {"thread_id": conversation_id}}
        
        # Resume graph execution (pass None to continue from checkpoint)
        result = None
        try:
            async for event in graph.astream(
                None,  # None means continue from checkpoint
                config=config,
                stream_mode="values",
            ):
                result = event
        except Exception as e:
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
        if result:
            final_response = result.get("final_response", "")
            execution_result = result.get("execution_result")
            
            message = (
                f"Action {approval.action} for order {approval.order_id} has been {status.value.lower()}."
            )
            
            if execution_result and execution_result.get("success"):
                message += f" {execution_result.get('message', 'Action executed successfully.')}"
            elif execution_result and not execution_result.get("success"):
                message += f" Note: {execution_result.get('error', 'Action execution failed.')}"
            
            if final_response:
                message += f" Agent response: {final_response}"
        else:
            message = (
                f"Action {approval.action} for order {approval.order_id} has been {status.value.lower()}."
            )
        
        return ApprovalResponse(
            status=status.value.lower(),
            message=message,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing approval: {str(e)}")

