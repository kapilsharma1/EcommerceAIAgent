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