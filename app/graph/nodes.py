"""LangGraph node implementations."""
import logging
import re
from typing import Dict, Any
from langsmith import traceable
from app.graph.state import AgentState
from app.llm.client import LLMClient, normalize_llm_response_dict
from app.rag.chroma_client import ChromaClient
from app.guardrails.validator import GuardrailsValidator
from app.actions.mock_order_service import mock_order_service
from app.models.domain import NextStep, ActionType

logger = logging.getLogger(__name__)

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
    logger.info(">>> NODE: classify_intent - START")
    logger.info(f"Input state - user_message: {state.get('user_message')}")
    logger.info(f"Input state - iteration_count: {state.get('iteration_count', 0)}")
    
    iteration_count = state.get("iteration_count", 0) + 1
    next_step = NextStep.FETCH_ORDER.value
    
    result = {
        "iteration_count": iteration_count,
        "next_step": next_step,
    }
    
    logger.info(f"Output state - iteration_count: {iteration_count}")
    logger.info(f"Output state - next_step: {next_step}")
    logger.info(">>> NODE: classify_intent - END")
    
    return result


@traceable(name="fetch_order_data")
async def fetch_order_data(state: AgentState) -> Dict[str, Any]:
    """
    Fetch order data using order service.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with order data
    """
    logger.info(">>> NODE: fetch_order_data - START")
    logger.info(f"Input state - user_message: {state.get('user_message')}")
    logger.info(f"Input state - iteration_count: {state.get('iteration_count', 0)}")
    logger.info(f"Input state - next_step: {state.get('next_step')}")
    
    # Increment iteration count if we're looping back (next_step indicates we need order data)
    iteration_count = state.get("iteration_count", 0)
    if state.get("next_step") == NextStep.FETCH_ORDER.value:
        iteration_count += 1
        logger.info(f"Incrementing iteration_count for loop: {iteration_count}")
    
    user_message = state.get("user_message", "")
    
    # Extract order ID from message (improved extraction with punctuation removal)
    order_id = None
    logger.info(f"Extracting order ID from message: '{user_message}'")
    
    # Try to find order ID in various formats
    for word in user_message.split():
        if word.startswith("ORD-") or word.startswith("#"):
            # Remove # and all punctuation, keep alphanumeric and hyphens
            order_id = re.sub(r'[#?.,!;:]', '', word).strip()
            logger.info(f"Found order ID (raw): {order_id}")
            break
    
    # If no order ID found, try to extract numeric ID from message
    if not order_id:
        # Look for patterns like "order #12345" or "order 12345"
        numeric_match = re.search(r'(?:order|#)\s*(\d+)', user_message, re.IGNORECASE)
        if numeric_match:
            numeric_id = numeric_match.group(1)
            logger.info(f"Found numeric order ID: {numeric_id}")
            # Try to map to ORD- format (e.g., "12345" -> "ORD-12345" or find closest match)
            # First try direct format conversion
            order_id = f"ORD-{numeric_id.zfill(3)}"  # Pad to 3 digits: "12345" -> "ORD-12345"
            logger.info(f"Trying formatted order ID: {order_id}")
    
    if not order_id:
        logger.warning("No order ID found in user message")
    
    order_data = None
    if order_id:
        logger.info(f"Fetching order data for order_id: {order_id}")
        try:
            repository = mock_order_service.order_repository
            
            # First try exact match
            order_data = await repository.get_order(order_id)
            
            # If not found and order_id looks like a numeric ID, try to find matching order
            if not order_data and order_id.isdigit():
                logger.info(f"Exact match not found for {order_id}, checking available orders...")
                # Try different formats
                for fmt_id in [f"ORD-{order_id.zfill(3)}", f"ORD-{order_id}"]:
                    logger.debug(f"Trying format: {fmt_id}")
                    order_data = await repository.get_order(fmt_id)
                    if order_data:
                        logger.info(f"Found order with format conversion: {fmt_id}")
                        break
            
            # If still not found and order_id starts with ORD-, try without prefix
            if not order_data and order_id.startswith("ORD-"):
                numeric_part = order_id.replace("ORD-", "")
                # Try to find order by matching numeric part
                available_orders = ['ORD-001', 'ORD-002', 'ORD-003', 'ORD-004', 'ORD-005']
                for avail_id in available_orders:
                    if numeric_part in avail_id or avail_id.endswith(numeric_part):
                        logger.info(f"Trying fuzzy match: {avail_id}")
                        order_data = await repository.get_order(avail_id)
                        if order_data:
                            logger.info(f"Found order with fuzzy match: {avail_id}")
                            break
            
            if order_data:
                logger.info(f"Order data retrieved successfully: order_id={order_data.order_id}, status={order_data.status}")
            else:
                logger.warning(f"Order not found for order_id: {order_id} after all attempts")
        except Exception as e:
            logger.error(f"Error fetching order data: {str(e)}", exc_info=True)
    else:
        logger.info("Skipping order fetch - no order_id extracted")
    
    next_step = NextStep.FETCH_POLICY.value if order_data else NextStep.NONE.value
    
    result = {
        "order_data": order_data.model_dump(mode="json") if order_data else None,
        "next_step": next_step,
        "iteration_count": iteration_count,  # Include updated iteration count
    }
    
    logger.info(f"Output state - order_data: {'present' if order_data else 'None'}")
    logger.info(f"Output state - next_step: {next_step}")
    logger.info(f"Output state - iteration_count: {iteration_count}")
    logger.info(">>> NODE: fetch_order_data - END")
    
    return result


@traceable(name="retrieve_policy")
async def retrieve_policy(state: AgentState) -> Dict[str, Any]:
    """
    Retrieve policy context using RAG.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with policy context
    """
    logger.info(">>> NODE: retrieve_policy - START")
    logger.info(f"Input state - user_message: {state.get('user_message')}")
    logger.info(f"Input state - order_data: {'present' if state.get('order_data') else 'None'}")
    logger.info(f"Input state - iteration_count: {state.get('iteration_count', 0)}")
    logger.info(f"Input state - next_step: {state.get('next_step')}")
    
    # Increment iteration count if we're looping back (next_step indicates we need policy data)
    iteration_count = state.get("iteration_count", 0)
    if state.get("next_step") == NextStep.FETCH_POLICY.value:
        iteration_count += 1
        logger.info(f"Incrementing iteration_count for loop: {iteration_count}")
    
    user_message = state.get("user_message", "")
    order_data = state.get("order_data")
    
    # Build query from user message and order context
    query = user_message
    if order_data:
        query += f" order status: {order_data.get('status')}"
    
    logger.info(f"Query for policy retrieval: {query}")
    
    # Query ChromaDB for policies
    try:
        logger.info("Querying ChromaDB for policies...")
        policy_chunks = await chroma_client.query_policies(query, top_k=3)
        logger.info(f"Retrieved {len(policy_chunks)} policy chunks")
        for i, chunk in enumerate(policy_chunks):
            logger.debug(f"Policy chunk {i+1}: score={chunk.get('score', 'N/A')}, text_length={len(chunk.get('text', ''))}")
    except Exception as e:
        logger.error(f"Error querying policies: {str(e)}", exc_info=True)
        policy_chunks = []
    
    # Combine policy chunks into context
    policy_context = "\n\n".join([
        f"Policy {i+1} (score: {chunk['score']:.2f}):\n{chunk['text']}"
        for i, chunk in enumerate(policy_chunks)
    ]) if policy_chunks else None
    
    result = {
        "policy_context": policy_context,
        "next_step": NextStep.NONE.value,
        "iteration_count": iteration_count,  # Include updated iteration count
    }
    
    logger.info(f"Output state - policy_context: {'present' if policy_context else 'None'}")
    logger.info(f"Output state - next_step: {result['next_step']}")
    logger.info(f"Output state - iteration_count: {iteration_count}")
    logger.info(">>> NODE: retrieve_policy - END")
    
    return result


@traceable(name="llm_reasoning")
async def llm_reasoning(state: AgentState) -> Dict[str, Any]:
    """
    LLM reasoning node to make decision.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with agent decision
    """
    logger.info(">>> NODE: llm_reasoning - START")
    logger.info(f"Input state - user_message: {state.get('user_message')}")
    logger.info(f"Input state - order_data: {'present' if state.get('order_data') else 'None'}")
    logger.info(f"Input state - policy_context: {'present' if state.get('policy_context') else 'None'}")
    
    user_message = state.get("user_message", "")
    conversation_history = state.get("conversation_history", [])
    order_data = state.get("order_data")
    policy_context = state.get("policy_context")
    
    # Convert order_data dict back to Order if needed
    order_obj = None
    if order_data:
        logger.info("Converting order_data dict to Order object...")
        try:
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
            logger.info(f"Order object created: order_id={order_obj.order_id}, status={order_obj.status}")
        except Exception as e:
            logger.error(f"Error converting order_data: {str(e)}", exc_info=True)
    
    # Get LLM decision
    order_dict = None
    if order_obj:
        order_dict = order_obj.model_dump(mode="json")
    
    # Add current date to context for time-based decision making
    from datetime import date
    current_date = date.today()
    logger.info(f"Current date: {current_date}")
    
    logger.info("Calling LLM client for agent decision...")
    try:
        llm_response, next_step = await llm_client.get_agent_decision(
            user_message=user_message,
            conversation_history=conversation_history,
            order_data=order_dict,
            policy_context=policy_context,
            current_date=current_date,
        )
        logger.info(f"LLM response received - action: {llm_response.action}, confidence: {llm_response.confidence}")
        logger.info(f"LLM response - final_answer: {llm_response.final_answer[:100]}..." if len(llm_response.final_answer) > 100 else f"LLM response - final_answer: {llm_response.final_answer}")
        logger.info(f"LLM response - next_step: {next_step}")
    except Exception as e:
        logger.error(f"Error getting LLM decision: {str(e)}", exc_info=True)
        raise
    
    result = {
        "agent_decision": llm_response.model_dump(mode="json"),
        "confidence": llm_response.confidence,
        "next_step": next_step,  # Set next_step in state from LLM decision
    }
    
    logger.info(f"Output state - agent_decision: present")
    logger.info(f"Output state - confidence: {llm_response.confidence}")
    logger.info(f"Output state - next_step: {next_step}")
    logger.info(">>> NODE: llm_reasoning - END")
    
    return result


@traceable(name="output_guardrails")
def output_guardrails(state: AgentState) -> Dict[str, Any]:
    """
    Validate LLM output using guardrails.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with validated decision
    """
    logger.info(">>> NODE: output_guardrails - START")
    logger.info(f"Input state - agent_decision: {'present' if state.get('agent_decision') else 'None'}")
    
    agent_decision_dict = state.get("agent_decision")
    
    if not agent_decision_dict:
        logger.warning("No agent_decision in state, creating fallback response")
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
        result = {
            "agent_decision": fallback.model_dump(mode="json"),
            "next_step": NextStep.NONE.value,
        }
        logger.info("Returning fallback response")
        logger.info(">>> NODE: output_guardrails - END")
        return result
    
    logger.info(f"Validating agent_decision: action={agent_decision_dict.get('action')}, confidence={agent_decision_dict.get('confidence')}")
    
    # Validate using guardrails
    try:
        validated_decision = guardrails_validator.validate(agent_decision_dict)
        logger.info(f"Validation successful - action: {validated_decision.action}, confidence: {validated_decision.confidence}")
    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        raise
    
    result = {
        "agent_decision": validated_decision.model_dump(mode="json"),
        "confidence": validated_decision.confidence,
    }
    
    logger.info(f"Output state - agent_decision: validated")
    logger.info(f"Output state - confidence: {validated_decision.confidence}")
    logger.info(">>> NODE: output_guardrails - END")
    
    return result


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
    logger.info(">>> NODE: human_approval - START")
    logger.info(f"Input state - agent_decision: {'present' if state.get('agent_decision') else 'None'}")
    logger.info(f"Input state - approval_id: {state.get('approval_id')}")
    
    agent_decision_dict = state.get("agent_decision")
    if not agent_decision_dict:
        logger.warning("No agent_decision in state, returning empty update")
        logger.info(">>> NODE: human_approval - END")
        return {}
    
    from app.models.domain import LLMResponse, ActionType
    # Normalize the dict to ensure proper enum types
    try:
        normalized_dict = normalize_llm_response_dict(agent_decision_dict)
        decision = LLMResponse(**normalized_dict)
        logger.info(f"Decision parsed - action: {decision.action}, order_id: {decision.order_id}")
    except Exception as e:
        logger.error(f"Error parsing agent_decision: {str(e)}", exc_info=True)
        logger.info(">>> NODE: human_approval - END")
        return {}
    
    # Only create approval if action is not NONE
    if decision.action == ActionType.NONE:
        logger.info("Action is NONE, no approval needed")
        logger.info(">>> NODE: human_approval - END")
        return {}
    
    # Check if approval already exists (from a previous run before interrupt)
    approval_id = state.get("approval_id")
    if approval_id:
        logger.info(f"Approval already exists: {approval_id}, fetching current status...")
        # Approval was created before interrupt, fetch current status
        try:
            approval = await approval_service.get_approval(approval_id)
            if approval:
                logger.info(f"Approval status: {approval.status}")
                result = {
                    "approval_id": approval.approval_id,
                    "approval_status": approval.status,
                }
                logger.info(">>> NODE: human_approval - END")
                return result
            else:
                logger.warning(f"Approval {approval_id} not found")
        except Exception as e:
            logger.error(f"Error fetching approval: {str(e)}", exc_info=True)
    
    # Create new approval request
    logger.info(f"Creating new approval request - order_id: {decision.order_id}, action: {decision.action}")
    try:
        approval = await approval_service.create_approval(
            order_id=decision.order_id,
            action=decision.action,
        )
        logger.info(f"Approval created: {approval.approval_id}, status: {approval.status}")
    except Exception as e:
        logger.error(f"Error creating approval: {str(e)}", exc_info=True)
        raise
    
    # Store approval_id -> conversation_id mapping for graph resumption
    # Access conversation_id from state (stored by API route)
    conversation_id = state.get("_conversation_id")
    if conversation_id:
        logger.info(f"Storing approval mapping: {approval.approval_id} -> {conversation_id}")
        # Import here to avoid circular dependency
        from app.api.approval_mapping import approval_to_conversation
        approval_to_conversation[approval.approval_id] = conversation_id
    else:
        logger.warning("No conversation_id in state, cannot store approval mapping")
    
    # Return approval info (status will be PENDING for new approvals)
    result = {
        "approval_id": approval.approval_id,
        "approval_status": approval.status,
    }
    
    logger.info(f"Output state - approval_id: {approval.approval_id}")
    logger.info(f"Output state - approval_status: {approval.status}")
    logger.info(">>> NODE: human_approval - END")
    
    return result


@traceable(name="execute_write_action")
async def execute_write_action(state: AgentState) -> Dict[str, Any]:
    """
    Execute write action after approval.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with execution result
    """
    logger.info(">>> NODE: execute_write_action - START")
    logger.info(f"Input state - agent_decision: {'present' if state.get('agent_decision') else 'None'}")
    logger.info(f"Input state - approval_status: {state.get('approval_status')}")
    
    agent_decision_dict = state.get("agent_decision")
    if not agent_decision_dict:
        logger.warning("No agent_decision in state, returning empty update")
        logger.info(">>> NODE: execute_write_action - END")
        return {}
    
    from app.models.domain import LLMResponse, ActionType
    # Normalize the dict to ensure proper enum types
    try:
        normalized_dict = normalize_llm_response_dict(agent_decision_dict)
        decision = LLMResponse(**normalized_dict)
        logger.info(f"Decision parsed - action: {decision.action}, order_id: {decision.order_id}")
    except Exception as e:
        logger.error(f"Error parsing agent_decision: {str(e)}", exc_info=True)
        logger.info(">>> NODE: execute_write_action - END")
        return {}
    
    # Execute action
    logger.info(f"Executing action: {decision.action} for order: {decision.order_id}")
    try:
        result = await mock_order_service.execute_action(
            action=decision.action,
            order_id=decision.order_id,
        )
        logger.info(f"Action executed - success: {result.get('success')}, message: {result.get('message', 'N/A')}")
        if not result.get('success'):
            logger.warning(f"Action execution failed - error: {result.get('error', 'N/A')}")
    except Exception as e:
        logger.error(f"Error executing action: {str(e)}", exc_info=True)
        result = {
            "success": False,
            "error": str(e),
        }
    
    output = {
        "execution_result": result,
    }
    
    logger.info(f"Output state - execution_result: {result}")
    logger.info(">>> NODE: execute_write_action - END")
    
    return output


@traceable(name="format_final_response")
def format_final_response(state: AgentState) -> Dict[str, Any]:
    """
    Format final response to user.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with final response
    """
    logger.info(">>> NODE: format_final_response - START")
    logger.info(f"Input state - agent_decision: {'present' if state.get('agent_decision') else 'None'}")
    logger.info(f"Input state - execution_result: {'present' if state.get('execution_result') else 'None'}")
    
    agent_decision_dict = state.get("agent_decision")
    execution_result = state.get("execution_result")
    
    if not agent_decision_dict:
        logger.warning("No agent_decision in state, returning default fallback response")
        result = {
            "final_response": "I apologize, but I couldn't process your request.",
        }
        logger.info(f"Output state - final_response: {result['final_response']}")
        logger.info(">>> NODE: format_final_response - END")
        return result
    
    from app.models.domain import LLMResponse
    # Normalize the dict to ensure proper enum types
    try:
        normalized_dict = normalize_llm_response_dict(agent_decision_dict)
        decision = LLMResponse(**normalized_dict)
        logger.info(f"Decision parsed - final_answer length: {len(decision.final_answer)}")
    except Exception as e:
        logger.error(f"Error parsing agent_decision: {str(e)}", exc_info=True)
        result = {
            "final_response": "I apologize, but I couldn't process your request.",
        }
        logger.info(">>> NODE: format_final_response - END")
        return result
    
    # Build final response
    response = decision.final_answer
    logger.info(f"Base response: {response[:100]}..." if len(response) > 100 else f"Base response: {response}")
    
    # Add execution result if available
    if execution_result and execution_result.get("success"):
        message = execution_result.get('message', 'Action completed successfully.')
        response += f"\n\n{message}"
        logger.info(f"Added execution success message: {message}")
    elif execution_result and not execution_result.get("success"):
        error = execution_result.get('error', 'Action could not be completed.')
        response += f"\n\nNote: {error}"
        logger.info(f"Added execution error message: {error}")
    
    # Update conversation_history with this exchange
    conversation_history = state.get("conversation_history", [])
    user_message = state.get("user_message", "")
    
    # Add user message and assistant response to history
    updated_history = conversation_history.copy()
    if user_message:
        updated_history.append({
            "role": "user",
            "content": user_message
        })
    updated_history.append({
        "role": "assistant",
        "content": response
    })
    
    result = {
        "final_response": response,
        "conversation_history": updated_history,  # Save updated history to checkpoint
    }
    
    logger.info(f"Output state - final_response length: {len(response)}")
    logger.info(f"Output state - final_response: {response[:200]}..." if len(response) > 200 else f"Output state - final_response: {response}")
    logger.info(f"Output state - conversation_history: {len(updated_history)} messages (added 2 new messages)")
    logger.info(">>> NODE: format_final_response - END")
    
    return result

