"""FastAPI request/response schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request schema."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")


class ChatResponse(BaseModel):
    """Chat response schema."""
    response: str = Field(..., description="Agent response")
    requires_approval: bool = Field(..., description="Whether approval is required")
    approval_id: Optional[str] = Field(None, description="Approval ID if required")


class ApprovalRequest(BaseModel):
    """Approval request schema."""
    status: str = Field(..., description="Approval status: APPROVED or REJECTED")


class ApprovalResponse(BaseModel):
    """Approval response schema."""
    status: str = Field(..., description="Approval status")
    message: str = Field(..., description="Status message")


class ConversationHistoryItem(BaseModel):
    """Conversation history item schema."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ConversationHistoryResponse(BaseModel):
    """Conversation history response schema."""
    conversation_id: str = Field(..., description="Conversation ID")
    messages: list[ConversationHistoryItem] = Field(..., description="List of conversation messages")


class ConversationListItem(BaseModel):
    """Conversation list item schema."""
    conversation_id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    last_message: Optional[str] = Field(None, description="Last message preview")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class ConversationListResponse(BaseModel):
    """Conversation list response schema."""
    conversations: list[ConversationListItem] = Field(..., description="List of conversations")


class DelayedOrderResponse(BaseModel):
    """Delayed order creation response schema."""
    order_id: str = Field(..., description="ID of the created delayed order")
    message: str = Field(..., description="Success message")


class OrderListItem(BaseModel):
    """Order list item schema."""
    order_id: str = Field(..., description="Order ID")
    status: str = Field(..., description="Order status")
    expected_delivery_date: str = Field(..., description="Expected delivery date")
    amount: float = Field(..., description="Order amount")
    refundable: bool = Field(..., description="Whether order is refundable")
    description: Optional[str] = Field(None, description="Order description")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class OrderListResponse(BaseModel):
    """Order list response schema."""
    orders: list[OrderListItem] = Field(..., description="List of orders")
    total: int = Field(..., description="Total number of orders")