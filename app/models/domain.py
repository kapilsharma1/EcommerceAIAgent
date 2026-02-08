"""Pydantic domain models with strict validation."""
from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PLACED = "PLACED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class ActionType(str, Enum):
    """Action type enumeration."""
    NONE = "NONE"
    CANCEL_ORDER = "CANCEL_ORDER"
    REFUND_ORDER = "REFUND_ORDER"


class ApprovalStatus(str, Enum):
    """Approval status enumeration."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class NextStep(str, Enum):
    """Next step enumeration."""
    NONE = "NONE"
    FETCH_ORDER = "FETCH_ORDER"
    FETCH_POLICY = "FETCH_POLICY"


class Order(BaseModel):
    """Order domain model."""
    order_id: str = Field(..., description="Unique order identifier")
    status: OrderStatus = Field(..., description="Current order status")
    expected_delivery_date: date = Field(..., description="Expected delivery date")
    amount: float = Field(..., gt=0, description="Order amount")
    refundable: bool = Field(..., description="Whether order is refundable")
    description: Optional[str] = Field(None, description="Order description")
    
    model_config = {
        "extra": "forbid",
        "strict": True,
        "json_encoders": {
            date: lambda v: v.isoformat() if v else None
        }
    }


class AgentDecision(BaseModel):
    """Agent decision model."""
    final_answer: str = Field(..., description="Final answer to the user")
    action: ActionType = Field(..., description="Proposed action")
    order_id: Optional[str] = Field(None, description="Order ID if action is not NONE")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    requires_human_approval: bool = Field(..., description="Whether human approval is required")
    
    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: Optional[str], info) -> Optional[str]:
        """Validate order_id is present when action is not NONE."""
        if info.data.get("action") != ActionType.NONE and not v:
            raise ValueError("order_id must be provided when action is not NONE")
        return v
    
    @field_validator("requires_human_approval")
    @classmethod
    def validate_approval_requirement(cls, v: bool, info) -> bool:
        """Validate requires_human_approval is true when action is not NONE."""
        if info.data.get("action") != ActionType.NONE and not v:
            raise ValueError("requires_human_approval must be true when action is not NONE")
        return v
    
    model_config = {"extra": "forbid", "strict": True}


class Approval(BaseModel):
    """Approval domain model."""
    approval_id: str = Field(..., description="Unique approval identifier")
    order_id: str = Field(..., description="Order ID for the approval")
    action: str = Field(..., description="Action to be approved")
    status: ApprovalStatus = Field(..., description="Approval status")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = {"extra": "forbid", "strict": True}


class LLMResponse(BaseModel):
    """LLM response schema matching the specified JSON structure."""
    analysis: str = Field(..., description="Analysis of the situation")
    final_answer: str = Field(..., description="Final answer to the user")
    action: ActionType = Field(..., description="Proposed action")
    order_id: Optional[str] = Field(None, description="Order ID if applicable")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    requires_human_approval: bool = Field(..., description="Whether human approval is required")
    
    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: Optional[str], info) -> Optional[str]:
        """Validate order_id is present when action is not NONE."""
        if info.data.get("action") != ActionType.NONE and not v:
            raise ValueError("order_id must be provided when action is not NONE")
        return v
    
    @field_validator("requires_human_approval")
    @classmethod
    def validate_approval_requirement(cls, v: bool, info) -> bool:
        """Validate requires_human_approval is true when action is not NONE."""
        if info.data.get("action") != ActionType.NONE and not v:
            raise ValueError("requires_human_approval must be true when action is not NONE")
        return v
    
    model_config = {"extra": "forbid", "strict": True}


class Conversation(BaseModel):
    """Conversation domain model."""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    title: str = Field(..., description="Conversation title")
    last_message: Optional[str] = Field(None, description="Last message preview")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {"extra": "forbid", "strict": True}
