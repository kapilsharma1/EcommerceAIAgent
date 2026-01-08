"""Mock order service for testing."""
from datetime import date, timedelta
from typing import Dict, Any, Optional
from app.models.domain import Order, OrderStatus
from app.actions.order_service import OrderService


class MockOrderRepository:
    """Mock order repository for testing."""
    
    def __init__(self):
        """Initialize with mock orders."""
        self.orders: Dict[str, Order] = {
            "ORD-001": Order(
                order_id="ORD-001",
                status=OrderStatus.PLACED,
                expected_delivery_date=date.today() + timedelta(days=5),
                amount=99.99,
                refundable=True,
            ),
            "ORD-002": Order(
                order_id="ORD-002",
                status=OrderStatus.SHIPPED,
                expected_delivery_date=date.today() + timedelta(days=2),
                amount=149.50,
                refundable=True,
            ),
            "ORD-003": Order(
                order_id="ORD-003",
                status=OrderStatus.DELIVERED,
                expected_delivery_date=date.today() - timedelta(days=3),
                amount=79.99,
                refundable=True,
            ),
            "ORD-004": Order(
                order_id="ORD-004",
                status=OrderStatus.CANCELLED,
                expected_delivery_date=date.today() + timedelta(days=7),
                amount=199.99,
                refundable=False,
            ),
            "ORD-005": Order(
                order_id="ORD-005",
                status=OrderStatus.PLACED,
                expected_delivery_date=date.today() - timedelta(days=10),  # Delayed
                amount=299.99,
                refundable=True,
            ),
        }
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)
    
    async def update_order_status(
        self,
        order_id: str,
        new_status: OrderStatus,
    ) -> Order:
        """Update order status."""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        
        order = self.orders[order_id]
        # Create new order with updated status
        updated_order = Order(
            order_id=order.order_id,
            status=new_status,
            expected_delivery_date=order.expected_delivery_date,
            amount=order.amount,
            refundable=order.refundable,
        )
        self.orders[order_id] = updated_order
        return updated_order
    
    async def process_refund(
        self,
        order_id: str,
        amount: float,
    ) -> Dict[str, Any]:
        """Process refund for order."""
        # In a real system, this would call payment gateway
        return {
            "refund_id": f"REF-{order_id}",
            "amount": amount,
            "status": "processed",
        }


# Create mock order service instance
mock_repository = MockOrderRepository()
mock_order_service = OrderService(mock_repository)

