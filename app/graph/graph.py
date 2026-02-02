"""LangGraph agent graph construction."""
import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from app.graph.state import AgentState
from app.graph.nodes import (
    classify_intent,
    fetch_order_data,
    retrieve_policy,
    llm_reasoning,
    output_guardrails,
    human_approval,
    check_approval_status,
    execute_write_action,
    format_final_response,
)
from app.models.domain import NextStep, ActionType, ApprovalStatus

logger = logging.getLogger(__name__)


def should_fetch_order(state: AgentState) -> Literal["fetch_order_data", "retrieve_policy", "llm_reasoning"]:
    """Conditional routing: should we fetch order data?"""
    next_step = state.get("next_step", NextStep.NONE.value)
    logger.debug(f"ROUTING: should_fetch_order - next_step: {next_step}")
    
    if next_step == NextStep.FETCH_ORDER.value:
        logger.info("ROUTING: -> fetch_order_data")
        return "fetch_order_data"
    elif next_step == NextStep.FETCH_POLICY.value:
        logger.info("ROUTING: -> retrieve_policy")
        return "retrieve_policy"
    
    logger.info("ROUTING: -> llm_reasoning")
    return "llm_reasoning"


def should_fetch_policy(state: AgentState) -> Literal["retrieve_policy", "llm_reasoning"]:
    """Conditional routing: should we fetch policy?"""
    next_step = state.get("next_step", NextStep.NONE.value)
    logger.debug(f"ROUTING: should_fetch_policy - next_step: {next_step}")
    
    if next_step == NextStep.FETCH_POLICY.value:
        logger.info("ROUTING: -> retrieve_policy")
        return "retrieve_policy"
    
    logger.info("ROUTING: -> llm_reasoning")
    return "llm_reasoning"


def should_require_approval(state: AgentState) -> Literal["human_approval", "execute_write_action", "format_final_response", "fetch_order_data", "retrieve_policy"]:
    """Conditional routing: does this require human approval or more data?"""
    agent_decision = state.get("agent_decision")
    logger.debug(f"ROUTING: should_require_approval - agent_decision: {'present' if agent_decision else 'None'}")
    
    # First check if we need more data (check next_step before routing to final response)
    next_step = state.get("next_step", NextStep.NONE.value)
    logger.debug(f"ROUTING: should_require_approval - next_step: {next_step}")
    
    # If next_step indicates we need more data, route back to fetch nodes
    if next_step == NextStep.FETCH_ORDER.value:
        iteration_count = state.get("iteration_count", 0)
        if iteration_count <= 5:  # Prevent infinite loops
            logger.info("ROUTING: -> fetch_order_data (next_step indicates need for order data)")
            return "fetch_order_data"
        else:
            logger.warning(f"ROUTING: Max iterations reached ({iteration_count}), going to final response")
    
    if next_step == NextStep.FETCH_POLICY.value:
        iteration_count = state.get("iteration_count", 0)
        if iteration_count <= 5:  # Prevent infinite loops
            logger.info("ROUTING: -> retrieve_policy (next_step indicates need for policy data)")
            return "retrieve_policy"
        else:
            logger.warning(f"ROUTING: Max iterations reached ({iteration_count}), going to final response")
    
    if not agent_decision:
        logger.info("ROUTING: -> format_final_response (no agent_decision)")
        return "format_final_response"
    
    action = agent_decision.get("action", ActionType.NONE.value)
    logger.debug(f"ROUTING: should_require_approval - action: {action}")
    
    # If action is not NONE, require approval
    if action != ActionType.NONE.value:
        approval_status = state.get("approval_status")
        logger.debug(f"ROUTING: should_require_approval - approval_status: {approval_status}")
        
        # If already approved, execute
        if approval_status == ApprovalStatus.APPROVED:
            logger.info("ROUTING: -> execute_write_action (already approved)")
            return "execute_write_action"
        
        # If rejected, skip to final response
        if approval_status == ApprovalStatus.REJECTED:
            logger.info("ROUTING: -> format_final_response (rejected)")
            return "format_final_response"
        
        # Otherwise, need approval
        logger.info("ROUTING: -> human_approval (action requires approval)")
        return "human_approval"
    
    logger.info("ROUTING: -> format_final_response (action is NONE and no data needed)")
    return "format_final_response"


def should_loop(state: AgentState) -> Literal["fetch_order_data", "retrieve_policy", "llm_reasoning", "format_final_response"]:
    """Conditional routing: should we loop for more information?"""
    iteration_count = state.get("iteration_count", 0)
    next_step = state.get("next_step", NextStep.NONE.value)
    logger.debug(f"ROUTING: should_loop - iteration_count: {iteration_count}, next_step: {next_step}")
    
    # Max iterations to prevent infinite loops
    if iteration_count > 5:
        logger.warning(f"ROUTING: -> format_final_response (max iterations reached: {iteration_count})")
        return "format_final_response"
    
    if next_step == NextStep.FETCH_ORDER.value:
        logger.info("ROUTING: -> fetch_order_data")
        return "fetch_order_data"
    elif next_step == NextStep.FETCH_POLICY.value:
        logger.info("ROUTING: -> retrieve_policy")
        return "retrieve_policy"
    elif next_step == NextStep.NONE.value:
        logger.info("ROUTING: -> format_final_response (next_step is NONE)")
        return "format_final_response"
    
    logger.info("ROUTING: -> llm_reasoning")
    return "llm_reasoning"


@traceable(name="build_agent_graph")
def build_agent_graph(approval_service, checkpointer=None):
    """
    Build the LangGraph agent graph.
    
    Args:
        approval_service: Approval service instance
        checkpointer: Optional checkpointer instance (if None, creates new MemorySaver)
        
    Returns:
        Compiled graph
    """
    logger.info("Building agent graph...")
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("fetch_order_data", fetch_order_data)
    workflow.add_node("retrieve_policy", retrieve_policy)
    workflow.add_node("llm_reasoning", llm_reasoning)
    workflow.add_node("output_guardrails", output_guardrails)
    
    # Human approval node - creates approval request
    async def human_approval_node(state: AgentState):
        """Human approval node wrapper - creates approval if needed."""
        return await human_approval(state, approval_service)
    
    # Check approval status node - validates status and interrupts if PENDING
    async def check_approval_status_node(state: AgentState):
        """Check approval status node wrapper - validates and interrupts if needed."""
        return await check_approval_status(state, approval_service)
    
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("check_approval_status", check_approval_status_node)
    workflow.add_node("execute_write_action", execute_write_action)
    workflow.add_node("format_final_response", format_final_response)
    
    # Set entry point
    workflow.set_entry_point("classify_intent")
    
    # Add edges
    workflow.add_edge("classify_intent", "fetch_order_data")
    
    # Conditional routing after fetch_order_data
    workflow.add_conditional_edges(
        "fetch_order_data",
        should_fetch_policy,
        {
            "retrieve_policy": "retrieve_policy",
            "llm_reasoning": "llm_reasoning",
        }
    )
    
    # After retrieve_policy, go to llm_reasoning
    workflow.add_edge("retrieve_policy", "llm_reasoning")
    
    # After llm_reasoning, validate with guardrails
    workflow.add_edge("llm_reasoning", "output_guardrails")
    
    # After guardrails, check if we need to loop, require approval, or format response
    # This routing function checks both next_step (for looping) and action (for approval)
    workflow.add_conditional_edges(
        "output_guardrails",
        should_require_approval,
        {
            "fetch_order_data": "fetch_order_data",  # Loop back to fetch order data
            "retrieve_policy": "retrieve_policy",  # Loop back to retrieve policy
            "human_approval": "human_approval",
            "execute_write_action": "execute_write_action",
            "format_final_response": "format_final_response",
        }
    )
    
    # After human_approval, always go to check_approval_status
    workflow.add_edge("human_approval", "check_approval_status")
    
    # After check_approval_status, route based on approval status
    def route_after_approval_check(state: AgentState) -> Literal["execute_write_action", "format_final_response"]:
        """Route after checking approval status."""
        approval_status = state.get("approval_status")
        logger.debug(f"ROUTING: route_after_approval_check - approval_status: {approval_status}")
        
        if approval_status == ApprovalStatus.APPROVED:
            logger.info("ROUTING: -> execute_write_action (approved)")
            return "execute_write_action"
        else:  # REJECTED
            logger.info("ROUTING: -> format_final_response (rejected)")
            return "format_final_response"
    
    workflow.add_conditional_edges(
        "check_approval_status",
        route_after_approval_check,
        {
            "execute_write_action": "execute_write_action",
            "format_final_response": "format_final_response",
        }
    )
    
    # After execution, go to final response
    workflow.add_edge("execute_write_action", "format_final_response")
    
    # Final response ends
    workflow.add_edge("format_final_response", END)
    
    # Compile with memory for checkpointing (needed for interrupts)
    logger.info("Compiling graph with checkpointing...")
    if checkpointer is None:
        checkpointer = MemorySaver()
        logger.info("Created new MemorySaver checkpointer")
    else:
        logger.info("Using provided checkpointer instance")
    
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["check_approval_status"],  # Interrupt before checking approval status
    )
    
    logger.info("Agent graph built successfully")
    return app

