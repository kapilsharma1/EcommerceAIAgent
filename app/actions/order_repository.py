"""PostgreSQL order repository."""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.domain import Order, OrderStatus
from app.models.database import OrderDB

logger = logging.getLogger(__name__)


class OrderRepository:
    """PostgreSQL-based order repository."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize order repository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        logger.info(f"ORDER_REPO: get_order - order_id: {order_id}")
        try:
            stmt = select(OrderDB).where(OrderDB.order_id == order_id)
            result = await self.session.execute(stmt)
            order_db = result.scalar_one_or_none()
            
            if order_db:
                order = Order(
                    order_id=order_db.order_id,
                    status=order_db.status,
                    expected_delivery_date=order_db.expected_delivery_date,
                    amount=order_db.amount,
                    refundable=order_db.refundable,
                    description=order_db.description,
                )
                logger.info(f"ORDER_REPO: Order found - order_id: {order.order_id}, status: {order.status}")
                return order
            else:
                logger.warning(f"ORDER_REPO: Order not found - order_id: {order_id}")
                return None
        except Exception as e:
            logger.error(f"ORDER_REPO: Error fetching order {order_id}: {str(e)}", exc_info=True)
            return None
    
    async def update_order_status(
        self,
        order_id: str,
        new_status: OrderStatus,
    ) -> Order:
        """Update order status."""
        logger.info(f"ORDER_REPO: update_order_status - order_id: {order_id}, new_status: {new_status}")
        try:
            stmt = select(OrderDB).where(OrderDB.order_id == order_id)
            result = await self.session.execute(stmt)
            order_db = result.scalar_one_or_none()
            
            if not order_db:
                raise ValueError(f"Order {order_id} not found")
            
            order_db.status = new_status
            await self.session.commit()
            await self.session.refresh(order_db)
            
            order = Order(
                order_id=order_db.order_id,
                status=order_db.status,
                expected_delivery_date=order_db.expected_delivery_date,
                amount=order_db.amount,
                refundable=order_db.refundable,
                description=order_db.description,
            )
            logger.info(f"ORDER_REPO: Order status updated - order_id: {order_id}, status: {new_status}")
            return order
        except Exception as e:
            await self.session.rollback()
            logger.error(f"ORDER_REPO: Error updating order status: {str(e)}", exc_info=True)
            raise
    
    async def process_refund(
        self,
        order_id: str,
        amount: float,
    ) -> Dict[str, Any]:
        """Process refund for order."""
        # In a real system, this would call payment gateway
        logger.info(f"ORDER_REPO: process_refund - order_id: {order_id}, amount: {amount}")
        return {
            "refund_id": f"REF-{order_id}",
            "amount": amount,
            "status": "processed",
        }
    
    async def create_order(self, order: Order) -> Order:
        """Create a new order in the database."""
        logger.info(f"ORDER_REPO: create_order - order_id: {order.order_id}")
        try:
            order_db = OrderDB(
                order_id=order.order_id,
                status=order.status,
                expected_delivery_date=order.expected_delivery_date,
                amount=order.amount,
                refundable=order.refundable,
                description=order.description,
            )
            self.session.add(order_db)
            await self.session.commit()
            await self.session.refresh(order_db)
            
            logger.info(f"ORDER_REPO: Order created - order_id: {order.order_id}")
            return order
        except Exception as e:
            await self.session.rollback()
            logger.error(f"ORDER_REPO: Error creating order: {str(e)}", exc_info=True)
            raise
    
    async def order_exists(self, order_id: str) -> bool:
        """Check if an order exists."""
        try:
            stmt = select(OrderDB.order_id).where(OrderDB.order_id == order_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"ORDER_REPO: Error checking if order exists: {str(e)}", exc_info=True)
            return False
    
    async def list_all_orders(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Order]:
        """
        List all orders sorted by created_at descending.
        
        Args:
            limit: Maximum number of orders to return
            offset: Number of orders to skip
            
        Returns:
            List of Orders
        """
        logger.info(f"ORDER_REPO: list_all_orders - limit: {limit}, offset: {offset}")
        try:
            stmt = (
                select(OrderDB)
                .order_by(desc(OrderDB.created_at))
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            orders_db = result.scalars().all()
            
            orders = [
                Order(
                    order_id=order_db.order_id,
                    status=order_db.status,
                    expected_delivery_date=order_db.expected_delivery_date,
                    amount=order_db.amount,
                    refundable=order_db.refundable,
                    description=order_db.description,
                )
                for order_db in orders_db
            ]
            
            logger.info(f"ORDER_REPO: Found {len(orders)} orders")
            return orders
        except Exception as e:
            logger.error(f"ORDER_REPO: Error listing orders: {str(e)}", exc_info=True)
            return []