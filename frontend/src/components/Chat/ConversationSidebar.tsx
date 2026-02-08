import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getConversationList, deleteConversation } from '@/services/chatService'
import { formatRelativeTime } from '@/utils/formatters'
import { Button } from '../Common/Button'
import { LoadingSpinner } from '../Common/LoadingSpinner'

interface ConversationSidebarProps {
  currentConversationId: string | null
  onSelectConversation: (conversationId: string) => void
  onNewConversation: () => void
  isOpen: boolean
  onClose: () => void
}

export const ConversationSidebar = ({
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  isOpen,
  onClose,
}: ConversationSidebarProps) => {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['conversationList'],
    queryFn: getConversationList,
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  const deleteMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversationList'] })
      // If deleted conversation was current, switch to new one
      if (data?.conversations.some(c => c.conversation_id === currentConversationId)) {
        onNewConversation()
      }
    },
  })

  const handleDelete = (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation()
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      deleteMutation.mutate(conversationId)
    }
  }

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-64 bg-white border-r border-gray-200
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          flex flex-col
        `}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Conversations</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              onNewConversation()
              onClose()
            }}
            className="text-primary-600"
          >
            + New
          </Button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center p-8">
              <LoadingSpinner size="sm" />
            </div>
          ) : data?.conversations.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p>No conversations yet</p>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  onNewConversation()
                  onClose()
                }}
                className="mt-4"
              >
                Start New Conversation
              </Button>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {data?.conversations.map((conv) => (
                <div
                  key={conv.conversation_id}
                  onClick={() => {
                    onSelectConversation(conv.conversation_id)
                    onClose()
                  }}
                  className={`
                    p-4 cursor-pointer hover:bg-gray-50 transition-colors
                    ${currentConversationId === conv.conversation_id ? 'bg-primary-50 border-l-4 border-primary-600' : ''}
                  `}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {conv.title}
                      </h3>
                      {conv.last_message && (
                        <p className="text-xs text-gray-500 mt-1 truncate">
                          {conv.last_message}
                        </p>
                      )}
                      <p className="text-xs text-gray-400 mt-1">
                        {formatRelativeTime(conv.updated_at)}
                      </p>
                    </div>
                    <button
                      onClick={(e) => handleDelete(e, conv.conversation_id)}
                      className="ml-2 text-gray-400 hover:text-red-600 transition-colors flex-shrink-0"
                      aria-label="Delete conversation"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
