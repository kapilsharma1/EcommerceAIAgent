"""Database-based order service wrapper."""
import logging
from typing import Dict, Any, Optional
from app.actions.order_repository import OrderRepository
from app.actions.order_service import OrderService
from app.models.database import AsyncSessionLocal
from app.models.domain import ActionType

logger = logging.getLogger(__name__)


class DatabaseOrderService:
    """Wrapper for OrderService that manages database sessions."""
    
    async def get_order(self, order_id: str):
        """Get order by ID with proper session management."""
        async with AsyncSessionLocal() as session:
            repository = OrderRepository(session)
            return await repository.get_order(order_id)
    
    async def execute_action(
        self,
        action: ActionType,
        order_id: Optional[str],
    ) -> Dict[str, Any]:
        """Execute action with proper session management."""
        async with AsyncSessionLocal() as session:
            repository = OrderRepository(session)
            service = OrderService(repository)
            return await service.execute_action(action, order_id)


# Global instance
db_order_service = DatabaseOrderService()
