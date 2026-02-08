import type { PendingApproval } from '@/types/approval'

interface ApprovalCardProps {
  approval: PendingApproval
}

export const ApprovalCard = ({ approval }: ApprovalCardProps) => {
  const getActionLabel = (action: string) => {
    switch (action) {
      case 'CANCEL_ORDER':
        return 'Cancel Order'
      case 'REFUND_ORDER':
        return 'Refund Order'
      default:
        return action
    }
  }

  const getActionDescription = (action: string) => {
    switch (action) {
      case 'CANCEL_ORDER':
        return 'This will cancel the order and prevent it from being shipped.'
      case 'REFUND_ORDER':
        return 'This will process a refund for the order amount.'
      default:
        return ''
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Action Required: {getActionLabel(approval.action)}
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          {getActionDescription(approval.action)}
        </p>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700">Order ID</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">
              {approval.orderId}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Agent Message:</strong> {approval.message}
        </p>
      </div>
    </div>
  )
}
