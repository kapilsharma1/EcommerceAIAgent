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

