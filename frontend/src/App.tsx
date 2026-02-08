import { useState } from 'react'
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChatContainer } from './components/Chat/ChatContainer'
import { ConversationSidebar } from './components/Chat/ConversationSidebar'
import { OrdersPage } from './components/Order/OrdersPage'
import { useConversation } from './hooks/useConversation'
import { createDelayedOrder, getAllOrders } from './services/orderService'
import './App.css'

type Page = 'chat' | 'orders'

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function AppContent() {
  const { conversationId, switchConversation, createNewConversation } = useConversation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [createdOrderId, setCreatedOrderId] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState<Page>('chat')
  const queryClient = useQueryClient()
  
  // Query orders for header info
  const { data: ordersData, refetch: refetchOrders } = useQuery({
    queryKey: ['orders'],
    queryFn: () => getAllOrders(100, 0),
    enabled: currentPage === 'orders',
  })

  const createOrderMutation = useMutation({
    mutationFn: createDelayedOrder,
    onSuccess: (data) => {
      setCreatedOrderId(data.order_id)
      // Invalidate orders query to refresh the orders list
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      // Clear the order ID after 5 seconds
      setTimeout(() => setCreatedOrderId(null), 5000)
    },
    onError: (error) => {
      console.error('Failed to create delayed order:', error)
      setCreatedOrderId('Error creating order')
      setTimeout(() => setCreatedOrderId(null), 5000)
    },
  })

  return (
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
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-gray-900">
                  {currentPage === 'chat' ? 'E-Commerce AI Customer Support' : 'All Orders'}
                </h1>
                <div className="flex items-center gap-4 mt-1">
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage('chat')}
                      className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                        currentPage === 'chat'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Chat
                    </button>
                    <button
                      onClick={() => setCurrentPage('orders')}
                      className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                        currentPage === 'orders'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Orders
                    </button>
                  </div>
                  {currentPage === 'chat' && (
                    <p className="text-sm text-gray-600">
                      Conversation ID: {conversationId?.substring(0, 20)}...
                    </p>
                  )}
                  {currentPage === 'orders' && ordersData && (
                    <p className="text-sm text-gray-600">
                      {ordersData.total} {ordersData.total === 1 ? 'order' : 'orders'} total
                    </p>
                  )}
                </div>
                {createdOrderId && (
                  <p className="text-sm font-semibold text-green-600 mt-1">
                    ✓ Created Order ID: {createdOrderId}
                  </p>
                )}
              </div>
              {currentPage === 'chat' ? (
                <button
                  onClick={() => createOrderMutation.mutate()}
                  disabled={createOrderMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
                >
                  {createOrderMutation.isPending ? 'Creating...' : 'Create Delayed Order'}
                </button>
              ) : (
                <button
                  onClick={() => refetchOrders()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Refresh
                </button>
              )}
            </div>
          </div>
        </header>
        
        <main className="flex-1 overflow-hidden">
          {currentPage === 'chat' ? (
            <ChatContainer conversationId={conversationId} />
          ) : (
            <OrdersPage />
          )}
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}

export default App
