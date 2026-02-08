import { useState, useCallback, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { sendMessage, getConversationHistory } from '@/services/chatService'
import type { Message } from '@/types/chat'
import type { PendingApproval } from '@/types/approval'

export const useChat = (conversationId: string | null) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null)

  // Fetch conversation history when conversationId is available
  const { data: historyData, isLoading: isLoadingHistory, refetch: refetchHistory } = useQuery({
    queryKey: ['conversationHistory', conversationId],
    queryFn: () => {
      if (!conversationId) throw new Error('No conversation ID')
      return getConversationHistory(conversationId)
    },
    enabled: !!conversationId,
    staleTime: 0, // Always refetch to get latest history
  })

  // Load conversation history into messages state whenever history data changes
  useEffect(() => {
    if (historyData && historyData.messages.length > 0) {
      const historyMessages: Message[] = historyData.messages.map((msg, index) => ({
        id: `history-${index}-${msg.role}-${msg.content.substring(0, 20)}`,
        content: msg.content,
        role: msg.role,
        timestamp: new Date(), // We don't have timestamps from backend, use current time
      }))
      setMessages(historyMessages)
    } else if (historyData && historyData.messages.length === 0) {
      // Clear messages if history is empty
      setMessages([])
    }
  }, [historyData])

  const addMessage = useCallback((message: Message) => {
    setMessages((prev) => [...prev, message])
  }, [])

  const mutation = useMutation({
    mutationFn: (message: string) => sendMessage(message, conversationId),
    onSuccess: (response, userMessage) => {
      // Refetch history to get the latest messages from backend
      // This ensures we're in sync with the backend's conversation history
      refetchHistory().then(() => {
        // Handle approval requirement after history is refreshed
        if (response.requires_approval && response.approval_id) {
          // Extract order ID from response if possible
          const orderIdMatch = response.response.match(/order\s+(?:#)?([A-Z0-9-]+)/i)
          const orderId = orderIdMatch ? orderIdMatch[1] : 'Unknown'

          // Extract action type from response
          let action: 'CANCEL_ORDER' | 'REFUND_ORDER' = 'CANCEL_ORDER'
          if (response.response.toLowerCase().includes('refund')) {
            action = 'REFUND_ORDER'
          }

          setPendingApproval({
            approvalId: response.approval_id,
            orderId,
            action,
            message: response.response,
          })
        } else {
          setPendingApproval(null)
        }
      })
    },
    onError: (error) => {
      console.error('Chat error:', error)
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        content: 'Sorry, I encountered an error. Please try again.',
        role: 'assistant',
        timestamp: new Date(),
      }
      addMessage(errorMsg)
    },
  })

  const sendChatMessage = useCallback(
    (message: string) => {
      if (!message.trim() || mutation.isPending) return
      mutation.mutate(message)
    },
    [mutation]
  )

  const clearPendingApproval = useCallback(() => {
    setPendingApproval(null)
  }, [])

  const addApprovalResponse = useCallback((message: string) => {
    const approvalMsg: Message = {
      id: `approval-${Date.now()}`,
      content: message,
      role: 'assistant',
      timestamp: new Date(),
    }
    addMessage(approvalMsg)
  }, [addMessage])

  return {
    messages,
    sendMessage: sendChatMessage,
    isLoading: mutation.isPending || isLoadingHistory,
    error: mutation.error,
    pendingApproval,
    clearPendingApproval,
    addApprovalResponse,
    isLoadingHistory,
  }
}
