export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
}

export interface ChatRequest {
  message: string
  conversation_id: string | null
}

export interface ChatResponse {
  response: string
  requires_approval: boolean
  approval_id: string | null
}

export interface ChatState {
  messages: Message[]
  conversationId: string | null
  isLoading: boolean
  error: string | null
}
