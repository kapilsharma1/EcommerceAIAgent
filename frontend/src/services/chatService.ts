import apiClient from './api'
import type { ChatRequest, ChatResponse } from '@/types/chat'

export interface ConversationHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export interface ConversationHistoryResponse {
  conversation_id: string
  messages: ConversationHistoryItem[]
}

export const sendMessage = async (
  message: string,
  conversationId: string | null
): Promise<ChatResponse> => {
  const request: ChatRequest = {
    message,
    conversation_id: conversationId,
  }

  const response = await apiClient.post<ChatResponse>('/chat', request)
  return response.data
}

export const getConversationHistory = async (
  conversationId: string
): Promise<ConversationHistoryResponse> => {
  const response = await apiClient.get<ConversationHistoryResponse>(
    `/conversations/${conversationId}/history`
  )
  return response.data
}

export interface ConversationListItem {
  conversation_id: string
  title: string
  last_message: string | null
  created_at: string
  updated_at: string
}

export interface ConversationListResponse {
  conversations: ConversationListItem[]
}

export const getConversationList = async (): Promise<ConversationListResponse> => {
  const response = await apiClient.get<ConversationListResponse>('/conversations')
  return response.data
}

export const deleteConversation = async (conversationId: string): Promise<void> => {
  await apiClient.delete(`/conversations/${conversationId}`)
}
