"""FastAPI routes."""
import uuid
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

router = APIRouter()

# Store graph instances and checkpoints (in production, use Redis or database)
graph_instances: Dict[str, Any] = {}
checkpoints: Dict[str, MemorySaver] = {}


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
    try:
        # Initialize approval service
        approval_service = ApprovalService(db)
        
        # Build or get graph
        conversation_id = request.conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
        
        if conversation_id not in graph_instances:
            graph_instances[conversation_id] = build_agent_graph(approval_service)
            checkpoints[conversation_id] = MemorySaver()
        
        graph = graph_instances[conversation_id]
        checkpoint = checkpoints[conversation_id]
        
        # Prepare initial state
        initial_state: AgentState = {
            "user_message": request.message,
            "conversation_history": [],
            "order_data": None,
            "policy_context": None,
            "agent_decision": None,
            "approval_id": None,
            "approval_status": None,
            "execution_result": None,
            "confidence": 0.0,
            "iteration_count": 0,
            "next_step": "NONE",
            "final_response": None,
            # Store conversation_id in state for access in nodes
            "_conversation_id": conversation_id,
        }
        
        # Create config for checkpointing
        config = {"configurable": {"thread_id": conversation_id}}
        
        # Invoke graph
        result = None
        async for event in graph.astream(
            initial_state,
            config=config,
            stream_mode="values",
        ):
            result = event
        
        if not result:
            raise HTTPException(status_code=500, detail="Agent execution failed")
        
        # Check if approval is required
        approval_id = result.get("approval_id")
        requires_approval = approval_id is not None
        
        # Get final response
        final_response = result.get("final_response", "I apologize, but I couldn't process your request.")
        
        return ChatResponse(
            response=final_response,
            requires_approval=requires_approval,
            approval_id=approval_id,
        )
        
    except Exception as e:
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
        
        # Update approval
        approval_service = ApprovalService(db)
        status = ApprovalStatus.APPROVED if request.status.upper() == "APPROVED" else ApprovalStatus.REJECTED
        
        approval = await approval_service.update_approval(
            approval_id=approval_id,
            status=status,
        )
        
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        
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
        
        # Get graph instance for this conversation
        if conversation_id not in graph_instances:
            raise HTTPException(
                status_code=404,
                detail=f"Graph instance not found for conversation {conversation_id}"
            )
        
        graph = graph_instances[conversation_id]
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

