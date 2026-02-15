import { useEffect, useRef } from 'react'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'
import type { Message } from '@/types/chat'

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
  isLoadingHistory?: boolean
}

export const MessageList = ({ messages, isLoading, isLoadingHistory = false }: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Debug logging
  useEffect(() => {
    console.log('MessageList received messages:', messages.length)
    console.log('MessageList messages breakdown:', {
      total: messages.length,
      user: messages.filter(m => m.role === 'user').length,
      assistant: messages.filter(m => m.role === 'assistant').length,
      allMessages: messages.map(m => ({ id: m.id, role: m.role, content: m.content.substring(0, 30) }))
    })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-2">
      {messages.length === 0 && !isLoadingHistory && (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <p className="text-lg font-medium mb-2">Welcome to Customer Support</p>
            <p className="text-sm">Start a conversation by typing a message below</p>
          </div>
        </div>
      )}
      
      {messages.length === 0 && isLoadingHistory && (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <p className="text-lg font-medium mb-2">Loading conversation history...</p>
          </div>
        </div>
      )}
      
      {messages.map((message) => {
        console.log('Rendering message:', { id: message.id, role: message.role, content: message.content.substring(0, 30) })
        return <MessageBubble key={message.id} message={message} />
      })}
      
      {isLoading && <TypingIndicator />}
      
      <div ref={messagesEndRef} />
    </div>
  )
}
