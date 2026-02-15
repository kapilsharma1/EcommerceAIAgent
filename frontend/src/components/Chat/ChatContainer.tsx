import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { ApprovalModal } from '../Approval/ApprovalModal'
import { useChat } from '@/hooks/useChat'
import { useApproval } from '@/hooks/useApproval'
import { useEffect } from 'react'

interface ChatContainerProps {
  conversationId: string | null
}

export const ChatContainer = ({ conversationId }: ChatContainerProps) => {
  const { messages, sendMessage, isLoading, pendingApproval, clearPendingApproval, addApprovalResponse, isLoadingHistory } = useChat(conversationId)
  const { submitApproval, isLoading: isApproving, response: approvalResponse } = useApproval()

  useEffect(() => {
    if (approvalResponse) {
      // Add approval response as a message
      addApprovalResponse(approvalResponse.message)
      clearPendingApproval()
    }
  }, [approvalResponse, clearPendingApproval, addApprovalResponse])

  const handleApproval = (status: 'APPROVED' | 'REJECTED') => {
    if (pendingApproval) {
      submitApproval(pendingApproval.approvalId, status)
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="flex-1 flex flex-col overflow-hidden">
        <MessageList messages={messages} isLoading={isLoading} isLoadingHistory={isLoadingHistory} />
        <ChatInput onSendMessage={sendMessage} isLoading={isLoading} />
      </div>

      {pendingApproval && (
        <ApprovalModal
          approval={pendingApproval}
          onApprove={() => handleApproval('APPROVED')}
          onReject={() => handleApproval('REJECTED')}
          onClose={clearPendingApproval}
          isLoading={isApproving}
        />
      )}
    </div>
  )
}
