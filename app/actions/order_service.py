"""Transactional write action services for orders."""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from langsmith import traceable
from app.models.domain import Order, OrderStatus, ActionType

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order write operations."""
    
    def __init__(self, order_repository):
        """
        Initialize order service.
        
        Args:
            order_repository: Repository for order data access
        """
        self.order_repository = order_repository
    
    @traceable(name="cancel_order")
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order (transactional, idempotent).
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Execution status dictionary
        """
        try:
            # Fetch current order state
            order = await self.order_repository.get_order(order_id)
            
            if not order:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found",
                    "order_id": order_id,
                }
            
            # Revalidate order state - can only cancel PLACED or SHIPPED orders
            if order.status == OrderStatus.CANCELLED:
                # Idempotent: already cancelled
                return {
                    "success": True,
                    "message": f"Order {order_id} is already cancelled",
                    "order_id": order_id,
                    "status": "already_cancelled",
                }
            
            if order.status == OrderStatus.DELIVERED:
                return {
                    "success": False,
                    "error": f"Cannot cancel delivered order {order_id}",
                    "order_id": order_id,
                }
            
            # Transactional: update order status
            updated_order = await self.order_repository.update_order_status(
                order_id=order_id,
                new_status=OrderStatus.CANCELLED,
            )
            
            return {
                "success": True,
                "message": f"Order {order_id} cancelled successfully",
                "order_id": order_id,
                "status": "cancelled",
                "order": updated_order.dict() if hasattr(updated_order, 'dict') else updated_order,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to cancel order {order_id}: {str(e)}",
                "order_id": order_id,
            }
    
    @traceable(name="refund_order")
    async def refund_order(self, order_id: str) -> Dict[str, Any]:
        """
        Refund an order (transactional, idempotent).
        
        Args:
            order_id: Order ID to refund
            
        Returns:
            Execution status dictionary
        """
        try:
            # Fetch current order state
            order = await self.order_repository.get_order(order_id)
            
            if not order:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found",
                    "order_id": order_id,
                }
            
            # Revalidate order state - must be refundable
            if not order.refundable:
                return {
                    "success": False,
                    "error": f"Order {order_id} is not refundable",
                    "order_id": order_id,
                }
            
            # Check if already refunded (idempotent check)
            # In a real system, you'd have a refund status field
            # For now, we'll check if order is cancelled or delivered
            if order.status == OrderStatus.CANCELLED:
                # Already cancelled, consider refund processed
                return {
                    "success": True,
                    "message": f"Order {order_id} refund processed (order was cancelled)",
                    "order_id": order_id,
                    "status": "refunded",
                }
            
            # Transactional: process refund
            # In a real system, this would integrate with payment gateway
            refund_result = await self.order_repository.process_refund(
                order_id=order_id,
                amount=order.amount,
            )
            
            return {
                "success": True,
                "message": f"Refund of ${order.amount} processed for order {order_id}",
                "order_id": order_id,
                "status": "refunded",
                "amount": order.amount,
                "refund_id": refund_result.get("refund_id") if refund_result else None,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to refund order {order_id}: {str(e)}",
                "order_id": order_id,
            }
    
    @traceable(name="execute_write_action")
    async def execute_action(
        self,
        action: ActionType,
        order_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Execute a write action based on action type.
        
        Args:
            action: Action type to execute
            order_id: Order ID (required for non-NONE actions)
            
        Returns:
            Execution status dictionary
        """
        logger.info(f"ORDER_SERVICE: execute_action - START - action: {action}, order_id: {order_id}")
        
        if action == ActionType.NONE:
            logger.info("ORDER_SERVICE: Action is NONE, returning success")
            return {
                "success": True,
                "message": "No action to execute",
                "action": "NONE",
            }
        
        if not order_id:
            logger.warning("ORDER_SERVICE: order_id is required but not provided")
            return {
                "success": False,
                "error": "order_id is required for write actions",
                "action": action.value,
            }
        
        try:
            if action == ActionType.CANCEL_ORDER:
                logger.info(f"ORDER_SERVICE: Executing cancel_order for {order_id}")
                result = await self.cancel_order(order_id)
            elif action == ActionType.REFUND_ORDER:
                logger.info(f"ORDER_SERVICE: Executing refund_order for {order_id}")
                result = await self.refund_order(order_id)
            else:
                logger.error(f"ORDER_SERVICE: Unknown action: {action}")
                result = {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "action": action.value,
                }
            
            logger.info(f"ORDER_SERVICE: execute_action result - success: {result.get('success')}, message: {result.get('message', result.get('error', 'N/A'))}")
            logger.info("ORDER_SERVICE: execute_action - END")
            return result
        except Exception as e:
            logger.error(f"ORDER_SERVICE: Error executing action: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Error executing action: {str(e)}",
                "action": action.value,
            }

