import { Button } from '../Common/Button'

interface ApprovalActionsProps {
  onApprove: () => void
  onReject: () => void
  isLoading: boolean
}

export const ApprovalActions = ({ onApprove, onReject, isLoading }: ApprovalActionsProps) => {
  return (
    <div className="flex gap-3 justify-end mt-6">
      <Button
        variant="secondary"
        onClick={onReject}
        disabled={isLoading}
      >
        Reject
      </Button>
      <Button
        variant="primary"
        onClick={onApprove}
        isLoading={isLoading}
        disabled={isLoading}
      >
        Approve
      </Button>
    </div>
  )
}
