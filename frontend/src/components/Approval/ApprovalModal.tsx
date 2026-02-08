import { useEffect } from 'react'
import { ApprovalCard } from './ApprovalCard'
import { ApprovalActions } from './ApprovalActions'
import type { PendingApproval } from '@/types/approval'

interface ApprovalModalProps {
  approval: PendingApproval
  onApprove: () => void
  onReject: () => void
  onClose: () => void
  isLoading: boolean
}

export const ApprovalModal = ({
  approval,
  onApprove,
  onReject,
  onClose,
  isLoading,
}: ApprovalModalProps) => {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [onClose, isLoading])

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget && !isLoading) {
      onClose()
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">Action Approval Required</h2>
          {!isLoading && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Close"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>

        <div className="p-6">
          <ApprovalCard approval={approval} />
          <ApprovalActions
            onApprove={onApprove}
            onReject={onReject}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  )
}
