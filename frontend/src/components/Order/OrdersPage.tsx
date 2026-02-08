import { useQuery } from '@tanstack/react-query'
import { getAllOrders } from '@/services/orderService'
import { OrderCard } from './OrderCard'
import { LoadingSpinner } from '../Common/LoadingSpinner'
import { formatDate, formatRelativeTime } from '@/utils/formatters'

export const OrdersPage = () => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['orders'],
    queryFn: () => getAllOrders(100, 0),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h3 className="text-lg font-semibold text-red-800 mb-2">Error Loading Orders</h3>
          <p className="text-red-600 mb-4">
            {error instanceof Error ? error.message : 'Failed to load orders'}
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const orders = data?.orders || []
  const total = data?.total || 0

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6">
        {orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
                />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No orders</h3>
              <p className="mt-1 text-sm text-gray-500">
                There are no orders in the database yet.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {orders.map((order) => (
              <div key={order.order_id} className="relative">
                <OrderCard order={order} />
                <div className="mt-2 px-4 text-xs text-gray-500">
                  <p>Created: {formatDate(order.created_at)} ({formatRelativeTime(order.created_at)})</p>
                  {order.description && (
                    <p className="mt-1 text-gray-600 line-clamp-2">{order.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
