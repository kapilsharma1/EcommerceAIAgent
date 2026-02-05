import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChatContainer } from './components/Chat/ChatContainer'
import { ConversationSidebar } from './components/Chat/ConversationSidebar'
import { useConversation } from './hooks/useConversation'
import './App.css'

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  const { conversationId, switchConversation, createNewConversation } = useConversation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <QueryClientProvider client={queryClient}>
      <div className="h-screen flex">
        <ConversationSidebar
          currentConversationId={conversationId}
          onSelectConversation={switchConversation}
          onNewConversation={createNewConversation}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />
        
        <div className="flex-1 flex flex-col overflow-hidden">
          <header className="bg-white border-b border-gray-200 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="lg:hidden text-gray-600 hover:text-gray-900"
                  aria-label="Toggle sidebar"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">
                    E-Commerce AI Customer Support
                  </h1>
                  <p className="text-sm text-gray-600 mt-1">
                    Powered by AI • Conversation ID: {conversationId?.substring(0, 20)}...
                  </p>
                </div>
              </div>
            </div>
          </header>
          
          <main className="flex-1 overflow-hidden">
            <ChatContainer conversationId={conversationId} />
          </main>
        </div>
      </div>
    </QueryClientProvider>
  )
}

export default App
