"""Approval service for human-in-the-loop."""
import uuid
from typing import Optional
from langsmith import traceable
from app.models.domain import Approval, ApprovalStatus, ActionType
from app.approvals.repository import ApprovalRepository
from sqlalchemy.ext.asyncio import AsyncSession


class ApprovalService:
    """Service for approval management."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize approval service.
        
        Args:
            session: Database session
        """
        self.repository = ApprovalRepository(session)
    
    @traceable(name="create_approval_request")
    async def create_approval(
        self,
        order_id: str,
        action: ActionType,
    ) -> Approval:
        """
        Create an approval request.
        
        Args:
            order_id: Order ID
            action: Action to be approved
            
        Returns:
            Created Approval
        """
        approval_id = f"APR-{uuid.uuid4().hex[:8].upper()}"
        
        return await self.repository.create_approval(
            approval_id=approval_id,
            order_id=order_id,
            action=action.value,
        )
    
    @traceable(name="get_approval_status")
    async def get_approval(self, approval_id: str) -> Optional[Approval]:
        """
        Get approval by ID.
        
        Args:
            approval_id: Approval ID
            
        Returns:
            Approval if found, None otherwise
        """
        return await self.repository.get_approval(approval_id)
    
    @traceable(name="update_approval_status")
    async def update_approval(
        self,
        approval_id: str,
        status: ApprovalStatus,
    ) -> Optional[Approval]:
        """
        Update approval status.
        
        Args:
            approval_id: Approval ID
            status: New status (APPROVED or REJECTED)
            
        Returns:
            Updated Approval if found, None otherwise
        """
        if status not in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
            raise ValueError("Status must be APPROVED or REJECTED")
        
        return await self.repository.update_approval_status(
            approval_id=approval_id,
            status=status,
        )
    
    @traceable(name="check_approval_ready")
    async def is_approved(self, approval_id: str) -> bool:
        """
        Check if approval is approved.
        
        Args:
            approval_id: Approval ID
            
        Returns:
            True if approved, False otherwise
        """
        approval = await self.get_approval(approval_id)
        if not approval:
            return False
        
        return approval.status == ApprovalStatus.APPROVED
    
    @traceable(name="check_approval_rejected")
    async def is_rejected(self, approval_id: str) -> bool:
        """
        Check if approval is rejected.
        
        Args:
            approval_id: Approval ID
            
        Returns:
            True if rejected, False otherwise
        """
        approval = await self.get_approval(approval_id)
        if not approval:
            return False
        
        return approval.status == ApprovalStatus.REJECTED

