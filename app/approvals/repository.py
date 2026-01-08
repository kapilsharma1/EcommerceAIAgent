"""Approval repository for database operations."""
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.database import ApprovalDB
from app.models.domain import Approval, ApprovalStatus


class ApprovalRepository:
    """Repository for approval database operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize approval repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def create_approval(
        self,
        approval_id: str,
        order_id: str,
        action: str,
    ) -> Approval:
        """
        Create a new approval request.
        
        Args:
            approval_id: Unique approval identifier
            order_id: Order ID
            action: Action to be approved
            
        Returns:
            Created Approval
        """
        approval_db = ApprovalDB(
            approval_id=approval_id,
            order_id=order_id,
            action=action,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.session.add(approval_db)
        await self.session.commit()
        await self.session.refresh(approval_db)
        
        return self._db_to_domain(approval_db)
    
    async def get_approval(self, approval_id: str) -> Optional[Approval]:
        """
        Get approval by ID.
        
        Args:
            approval_id: Approval ID
            
        Returns:
            Approval if found, None otherwise
        """
        result = await self.session.execute(
            select(ApprovalDB).where(ApprovalDB.approval_id == approval_id)
        )
        approval_db = result.scalar_one_or_none()
        
        if not approval_db:
            return None
        
        return self._db_to_domain(approval_db)
    
    async def update_approval_status(
        self,
        approval_id: str,
        status: ApprovalStatus,
    ) -> Optional[Approval]:
        """
        Update approval status.
        
        Args:
            approval_id: Approval ID
            status: New status
            
        Returns:
            Updated Approval if found, None otherwise
        """
        await self.session.execute(
            update(ApprovalDB)
            .where(ApprovalDB.approval_id == approval_id)
            .values(
                status=status,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.commit()
        
        return await self.get_approval(approval_id)
    
    async def get_pending_approval_by_order(
        self,
        order_id: str,
    ) -> Optional[Approval]:
        """
        Get pending approval for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Pending Approval if found, None otherwise
        """
        result = await self.session.execute(
            select(ApprovalDB)
            .where(
                ApprovalDB.order_id == order_id,
                ApprovalDB.status == ApprovalStatus.PENDING
            )
            .order_by(ApprovalDB.created_at.desc())
        )
        approval_db = result.scalar_one_or_none()
        
        if not approval_db:
            return None
        
        return self._db_to_domain(approval_db)
    
    def _db_to_domain(self, approval_db: ApprovalDB) -> Approval:
        """Convert database model to domain model."""
        return Approval(
            approval_id=approval_db.approval_id,
            order_id=approval_db.order_id,
            action=approval_db.action,
            status=approval_db.status,
            created_at=approval_db.created_at,
        )

