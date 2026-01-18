"""LangGraph node implementations."""
from typing import Dict, Any
from langsmith import traceable
from app.graph.state import AgentState
from app.llm.client import LLMClient, normalize_llm_response_dict
from app.rag.chroma_client import ChromaClient
from app.guardrails.validator import GuardrailsValidator
from app.actions.mock_order_service import mock_order_service
from app.models.domain import NextStep, ActionType


# Initialize services
llm_client = LLMClient()
chroma_client = ChromaClient()
guardrails_validator = GuardrailsValidator()


@traceable(name="classify_intent")
def classify_intent(state: AgentState) -> Dict[str, Any]:
    """
    Classify user intent and initialize state.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state
    """
    return {
        "iteration_count": state.get("iteration_count", 0) + 1,
        "next_step": NextStep.FETCH_ORDER.value,
    }


@traceable(name="fetch_order_data")
async def fetch_order_data(state: AgentState) -> Dict[str, Any]:
    """
    Fetch order data using order service.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with order data
    """
    user_message = state.get("user_message", "")
    
    # Extract order ID from message (simple extraction)
    # In production, use more sophisticated extraction
    order_id = None
    for word in user_message.split():
        if word.startswith("ORD-") or word.startswith("#"):
            order_id = word.replace("#", "").strip()
            break
    
    order_data = None
    if order_id:
        repository = mock_order_service.order_repository
        order_data = await repository.get_order(order_id)
    
    return {
        "order_data": order_data.model_dump(mode="json") if order_data else None,
        "next_step": NextStep.FETCH_POLICY.value if order_data else NextStep.NONE.value,
    }


@traceable(name="retrieve_policy")
async def retrieve_policy(state: AgentState) -> Dict[str, Any]:
    """
    Retrieve policy context using RAG.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with policy context
    """
    user_message = state.get("user_message", "")
    order_data = state.get("order_data")
    
    # Build query from user message and order context
    query = user_message
    if order_data:
        query += f" order status: {order_data.get('status')}"
    
    # Query ChromaDB for policies
    policy_chunks = await chroma_client.query_policies(query, top_k=3)
    
    # Combine policy chunks into context
    policy_context = "\n\n".join([
        f"Policy {i+1} (score: {chunk['score']:.2f}):\n{chunk['text']}"
        for i, chunk in enumerate(policy_chunks)
    ])
    
    return {
        "policy_context": policy_context if policy_chunks else None,
        "next_step": NextStep.NONE.value,
    }


@traceable(name="llm_reasoning")
async def llm_reasoning(state: AgentState) -> Dict[str, Any]:
    """
    LLM reasoning node to make decision.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with agent decision
    """
    user_message = state.get("user_message", "")
    conversation_history = state.get("conversation_history", [])
    order_data = state.get("order_data")
    policy_context = state.get("policy_context")
    
    # Convert order_data dict back to Order if needed
    order_obj = None
    if order_data:
        from app.models.domain import Order, OrderStatus
        from datetime import date as date_type
        
        # Handle date if it's a string
        delivery_date = order_data["expected_delivery_date"]
        if isinstance(delivery_date, str):
            delivery_date = date_type.fromisoformat(delivery_date)
        
        order_obj = Order(
            order_id=order_data["order_id"],
            status=OrderStatus(order_data["status"]),
            expected_delivery_date=delivery_date,
            amount=order_data["amount"],
            refundable=order_data["refundable"],
        )
    
    # Get LLM decision
    order_dict = None
    if order_obj:
        order_dict = order_obj.model_dump(mode="json")
    
    llm_response, next_step = await llm_client.get_agent_decision(
        user_message=user_message,
        conversation_history=conversation_history,
        order_data=order_dict,
        policy_context=policy_context,
    )
    
    return {
        "agent_decision": llm_response.model_dump(mode="json"),
        "confidence": llm_response.confidence,
        "next_step": next_step,  # Set next_step in state from LLM decision
    }


@traceable(name="output_guardrails")
def output_guardrails(state: AgentState) -> Dict[str, Any]:
    """
    Validate LLM output using guardrails.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with validated decision
    """
    agent_decision_dict = state.get("agent_decision")
    
    if not agent_decision_dict:
        # Fallback if no decision
        from app.models.domain import LLMResponse, ActionType, NextStep
        fallback = LLMResponse(
            analysis="No decision available",
            final_answer="I apologize, but I couldn't process your request.",
            action=ActionType.NONE,
            order_id=None,
            confidence=0.0,
            requires_human_approval=False,
        )
        return {
            "agent_decision": fallback.model_dump(mode="json"),
            "next_step": NextStep.NONE.value,
        }
    
    # Validate using guardrails
    validated_decision = guardrails_validator.validate(agent_decision_dict)
    
    return {
        "agent_decision": validated_decision.model_dump(mode="json"),
        "confidence": validated_decision.confidence,
    }


@traceable(name="human_approval")
async def human_approval(state: AgentState, approval_service) -> Dict[str, Any]:
    """
    Create approval request and interrupt for human approval.
    
    Args:
        state: Current agent state
        approval_service: Approval service instance
        
    Returns:
        Updated state with approval_id and current approval_status
    """
    agent_decision_dict = state.get("agent_decision")
    if not agent_decision_dict:
        return {}
    
    from app.models.domain import LLMResponse, ActionType
    # Normalize the dict to ensure proper enum types
    normalized_dict = normalize_llm_response_dict(agent_decision_dict)
    decision = LLMResponse(**normalized_dict)
    
    # Only create approval if action is not NONE
    if decision.action == ActionType.NONE:
        return {}
    
    # Check if approval already exists (from a previous run before interrupt)
    approval_id = state.get("approval_id")
    if approval_id:
        # Approval was created before interrupt, fetch current status
        approval = await approval_service.get_approval(approval_id)
        if approval:
            # Return current status (may have been updated by human)
            return {
                "approval_id": approval.approval_id,
                "approval_status": approval.status,
            }
    
    # Create new approval request
    approval = await approval_service.create_approval(
        order_id=decision.order_id,
        action=decision.action,
    )
    
    # Store approval_id -> conversation_id mapping for graph resumption
    # Access conversation_id from state (stored by API route)
    conversation_id = state.get("_conversation_id")
    if conversation_id:
        # Import here to avoid circular dependency
        from app.api.approval_mapping import approval_to_conversation
        approval_to_conversation[approval.approval_id] = conversation_id
    
    # Return approval info (status will be PENDING for new approvals)
    return {
        "approval_id": approval.approval_id,
        "approval_status": approval.status,
    }


@traceable(name="execute_write_action")
async def execute_write_action(state: AgentState) -> Dict[str, Any]:
    """
    Execute write action after approval.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with execution result
    """
    agent_decision_dict = state.get("agent_decision")
    if not agent_decision_dict:
        return {}
    
    from app.models.domain import LLMResponse, ActionType
    # Normalize the dict to ensure proper enum types
    normalized_dict = normalize_llm_response_dict(agent_decision_dict)
    decision = LLMResponse(**normalized_dict)
    
    # Execute action
    result = await mock_order_service.execute_action(
        action=decision.action,
        order_id=decision.order_id,
    )
    
    return {
        "execution_result": result,
    }


@traceable(name="format_final_response")
def format_final_response(state: AgentState) -> Dict[str, Any]:
    """
    Format final response to user.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with final response
    """
    agent_decision_dict = state.get("agent_decision")
    execution_result = state.get("execution_result")
    
    if not agent_decision_dict:
        return {
            "final_response": "I apologize, but I couldn't process your request.",
        }
    
    from app.models.domain import LLMResponse
    # Normalize the dict to ensure proper enum types
    normalized_dict = normalize_llm_response_dict(agent_decision_dict)
    decision = LLMResponse(**normalized_dict)
    
    # Build final response
    response = decision.final_answer
    
    # Add execution result if available
    if execution_result and execution_result.get("success"):
        response += f"\n\n{execution_result.get('message', 'Action completed successfully.')}"
    elif execution_result and not execution_result.get("success"):
        response += f"\n\nNote: {execution_result.get('error', 'Action could not be completed.')}"
    
    return {
        "final_response": response,
    }

