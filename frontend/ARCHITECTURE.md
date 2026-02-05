# Frontend Architecture

## Overview

The frontend is built with React 18, TypeScript, and Tailwind CSS, following modern best practices for maintainability and scalability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │
│  │   App.tsx    │─────▶│ ChatContainer│─────▶│ Message  │  │
│  │              │      │              │      │  List    │  │
│  └──────────────┘      └──────────────┘      └──────────┘  │
│         │                      │                             │
│         │                      │                             │
│         ▼                      ▼                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   Hooks      │      │   Services   │                    │
│  │              │      │              │                    │
│  │ useChat      │─────▶│ chatService  │─────▶ Backend API  │
│  │ useApproval  │─────▶│ approvalSvc  │                    │
│  │ useConversation│    │              │                    │
│  └──────────────┘      └──────────────┘                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Sends Message

```
User Input → ChatInput → useChat.sendMessage() → chatService.sendMessage()
    ↓
Backend API (POST /api/v1/chat)
    ↓
Response → useChat mutation.onSuccess() → Add messages to state
    ↓
MessageList re-renders → Display messages
```

### 2. Approval Flow

```
Agent Response (requires_approval: true)
    ↓
useChat detects approval requirement → Set pendingApproval state
    ↓
ApprovalModal opens automatically
    ↓
User clicks Approve/Reject
    ↓
useApproval.submitApproval() → approvalService.submitApproval()
    ↓
Backend API (POST /api/v1/approvals/{id})
    ↓
Response → Add approval response message → Close modal
```

## Component Hierarchy

```
App
├── QueryClientProvider (React Query)
└── ChatContainer
    ├── MessageList
    │   ├── MessageBubble (for each message)
    │   └── TypingIndicator (when loading)
    ├── ChatInput
    └── ApprovalModal (conditional)
        ├── ApprovalCard
        └── ApprovalActions
```

## State Management

### React Query
- Handles API calls and caching
- Manages loading and error states
- Provides mutation hooks for chat and approvals

### Local State (useState)
- Messages array in `useChat` hook
- Pending approval state
- UI state (modals, inputs, etc.)

### localStorage
- Conversation ID persistence
- Maintains conversation context across sessions

## Key Design Decisions

### 1. Component Composition
- Small, focused components
- Reusable common components
- Clear separation of concerns

### 2. Custom Hooks
- Encapsulate business logic
- Reusable across components
- Easy to test

### 3. Type Safety
- Full TypeScript coverage
- Strict type checking
- Shared type definitions

### 4. API Layer
- Centralized API client (Axios)
- Service functions for each endpoint
- Consistent error handling

## File Organization

### Components
- **Chat/**: Chat-specific UI components
- **Approval/**: Approval modal and related components
- **Order/**: Order display components (for future use)
- **Common/**: Reusable UI primitives

### Hooks
- **useChat**: Manages chat state and messages
- **useApproval**: Handles approval submissions
- **useConversation**: Manages conversation IDs

### Services
- **api.ts**: Axios client configuration
- **chatService.ts**: Chat API functions
- **approvalService.ts**: Approval API functions

### Utils
- **conversationId.ts**: Conversation ID helpers
- **formatters.ts**: Date/currency formatting

## Styling Approach

### Tailwind CSS
- Utility-first CSS framework
- Consistent design system
- Responsive by default

### Custom Classes
- Defined in `tailwind.config.js`
- Extended color palette
- Reusable component styles

## Error Handling

1. **API Errors**: Caught by Axios interceptors
2. **Component Errors**: Displayed in UI with user-friendly messages
3. **Network Errors**: Handled gracefully with retry logic

## Performance Optimizations

1. **React Query Caching**: Reduces unnecessary API calls
2. **Component Memoization**: Prevents unnecessary re-renders
3. **Code Splitting**: Vite automatically splits code
4. **Lazy Loading**: Can be added for route-based splitting

## Testing Strategy (Future)

- Unit tests for hooks and utilities
- Component tests with React Testing Library
- Integration tests for API flows
- E2E tests for critical user paths

## Future Enhancements

1. **Real-time Updates**: WebSocket integration for streaming responses
2. **Conversation History**: Load previous conversations
3. **User Profiles**: User authentication and profiles
4. **Dark Mode**: Theme switching
5. **Accessibility**: ARIA labels and keyboard navigation
6. **Internationalization**: Multi-language support
