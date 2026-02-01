"""LangGraph state definition."""
from typing import TypedDict, List, Dict, Any, Optional
from app.models.domain import Order, LLMResponse, ApprovalStatus


class AgentState(TypedDict):
    """State for the LangGraph agent."""
    # User input
    user_message: str
    conversation_history: List[Dict[str, str]]
    
    # Data
    order_data: Optional[Order]
    policy_context: Optional[str]
    
    # Agent decision
    agent_decision: Optional[LLMResponse]
    
    # Approval
    approval_id: Optional[str]
    approval_status: Optional[ApprovalStatus]
    
    # Execution
    execution_result: Optional[Dict[str, Any]]
    
    # Control flow
    confidence: float
    iteration_count: int
    next_step: str
    
    # Final output
    final_response: Optional[str]
    
    # Internal metadata (not user-facing)
    _conversation_id: Optional[str]  # Conversation ID for checkpointing and approval mapping

