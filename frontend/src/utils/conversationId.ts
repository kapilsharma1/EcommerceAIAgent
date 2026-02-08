const CONVERSATION_ID_KEY = 'ecommerce_ai_conversation_id'

/**
 * Generate a new conversation ID
 */
export const generateConversationId = (): string => {
  return `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Get conversation ID from localStorage or generate a new one
 */
export const getOrCreateConversationId = (): string => {
  if (typeof window === 'undefined') {
    return generateConversationId()
  }

  const stored = localStorage.getItem(CONVERSATION_ID_KEY)
  if (stored) {
    return stored
  }

  const newId = generateConversationId()
  localStorage.setItem(CONVERSATION_ID_KEY, newId)
  return newId
}

/**
 * Clear conversation ID from localStorage
 */
export const clearConversationId = (): void => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(CONVERSATION_ID_KEY)
  }
}

/**
 * Set a specific conversation ID
 */
export const setConversationId = (id: string): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(CONVERSATION_ID_KEY, id)
  }
}
