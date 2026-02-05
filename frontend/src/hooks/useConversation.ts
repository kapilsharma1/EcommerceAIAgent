import { useState, useEffect } from 'react'
import { getOrCreateConversationId, clearConversationId as clearId, setConversationId as setConvId, generateConversationId } from '@/utils/conversationId'

export const useConversation = () => {
  const [conversationId, setConversationId] = useState<string | null>(null)

  useEffect(() => {
    const id = getOrCreateConversationId()
    setConversationId(id)
  }, [])

  const clearConversation = () => {
    clearId()
    const newId = generateConversationId()
    setConvId(newId)
    setConversationId(newId)
  }

  const switchConversation = (newId: string) => {
    setConvId(newId)
    setConversationId(newId)
    // Reload to refresh the chat
    window.location.reload()
  }

  const createNewConversation = () => {
    clearConversation()
    // Reload to start fresh
    window.location.reload()
  }

  return {
    conversationId,
    clearConversation,
    switchConversation,
    createNewConversation,
  }
}
