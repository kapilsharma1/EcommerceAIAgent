import { OrderStatusBadge } from './OrderStatusBadge'
import { formatDate, formatCurrency } from '@/utils/formatters'
import type { Order } from '@/types/order'

interface OrderCardProps {
  order: Order
  className?: string
}

export const OrderCard = ({ order, className }: OrderCardProps) => {
  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 ${className || ''}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Order {order.order_id}</h3>
          <p className="text-sm text-gray-500 mt-1">
            Expected delivery: {formatDate(order.expected_delivery_date)}
          </p>
        </div>
        <OrderStatusBadge status={order.status} />
      </div>
      
      <div className="flex items-center justify-between pt-3 border-t border-gray-200">
        <div>
          <p className="text-sm text-gray-600">Amount</p>
          <p className="text-lg font-semibold text-gray-900">
            {formatCurrency(order.amount)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-600">Refundable</p>
          <p className={`text-sm font-medium ${order.refundable ? 'text-green-600' : 'text-red-600'}`}>
            {order.refundable ? 'Yes' : 'No'}
          </p>
        </div>
      </div>
    </div>
  )
}
