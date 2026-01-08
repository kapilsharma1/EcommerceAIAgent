"""LangGraph agent graph construction."""
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
    execute_write_action,
    format_final_response,
)
from app.models.domain import NextStep, ActionType


def should_fetch_order(state: AgentState) -> Literal["fetch_order_data", "retrieve_policy", "llm_reasoning"]:
    """Conditional routing: should we fetch order data?"""
    next_step = state.get("next_step", NextStep.NONE.value)
    
    if next_step == NextStep.FETCH_ORDER.value:
        return "fetch_order_data"
    elif next_step == NextStep.FETCH_POLICY.value:
        return "retrieve_policy"
    
    return "llm_reasoning"


def should_fetch_policy(state: AgentState) -> Literal["retrieve_policy", "llm_reasoning"]:
    """Conditional routing: should we fetch policy?"""
    next_step = state.get("next_step", NextStep.NONE.value)
    
    if next_step == NextStep.FETCH_POLICY.value:
        return "retrieve_policy"
    
    return "llm_reasoning"


def should_require_approval(state: AgentState) -> Literal["human_approval", "execute_write_action", "format_final_response"]:
    """Conditional routing: does this require human approval?"""
    agent_decision = state.get("agent_decision")
    
    if not agent_decision:
        return "format_final_response"
    
    action = agent_decision.get("action", ActionType.NONE.value)
    
    # If action is not NONE, require approval
    if action != ActionType.NONE.value:
        approval_status = state.get("approval_status")
        
        # If already approved, execute
        if approval_status and str(approval_status) == "APPROVED":
            return "execute_write_action"
        
        # If rejected, skip to final response
        if approval_status and str(approval_status) == "REJECTED":
            return "format_final_response"
        
        # Otherwise, need approval
        return "human_approval"
    
    return "format_final_response"


def should_loop(state: AgentState) -> Literal["fetch_order_data", "retrieve_policy", "llm_reasoning", "format_final_response"]:
    """Conditional routing: should we loop for more information?"""
    iteration_count = state.get("iteration_count", 0)
    next_step = state.get("next_step", NextStep.NONE.value)
    
    # Max iterations to prevent infinite loops
    if iteration_count > 5:
        return "format_final_response"
    
    if next_step == NextStep.FETCH_ORDER.value:
        return "fetch_order_data"
    elif next_step == NextStep.FETCH_POLICY.value:
        return "retrieve_policy"
    elif next_step == NextStep.NONE.value:
        return "format_final_response"
    
    return "llm_reasoning"


@traceable(name="build_agent_graph")
def build_agent_graph(approval_service):
    """
    Build the LangGraph agent graph.
    
    Args:
        approval_service: Approval service instance
        
    Returns:
        Compiled graph
    """
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("fetch_order_data", fetch_order_data)
    workflow.add_node("retrieve_policy", retrieve_policy)
    workflow.add_node("llm_reasoning", llm_reasoning)
    workflow.add_node("output_guardrails", output_guardrails)
    
    # Human approval node (will interrupt)
    async def human_approval_node(state: AgentState):
        """
        Human approval node wrapper.
        
        Note: The graph interrupts BEFORE this node runs (via interrupt_before).
        When resumed, this node will:
        1. Check if approval already exists (from before interrupt)
        2. If exists, fetch current status (may have been updated)
        3. If not exists, create new approval
        4. Return approval info for routing
        """
        result = await human_approval(state, approval_service)
        # The interrupt happens BEFORE this node runs (via interrupt_before parameter)
        # When this node executes after resume, it will have the current approval status
        return result
    
    workflow.add_node("human_approval", human_approval_node)
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
    
    # After guardrails, check if we need to loop or require approval
    workflow.add_conditional_edges(
        "output_guardrails",
        should_require_approval,
        {
            "human_approval": "human_approval",
            "execute_write_action": "execute_write_action",
            "format_final_response": "format_final_response",
        }
    )
    
    # Human approval interrupts - will resume when approved
    workflow.add_conditional_edges(
        "human_approval",
        should_require_approval,
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
    memory = MemorySaver()
    app = workflow.compile(
        checkpointer=memory,
        interrupt_before=["human_approval"],  # Interrupt before human approval
    )
    
    return app

