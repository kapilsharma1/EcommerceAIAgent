# Conversation History Feature

## Overview

This feature allows the frontend to automatically load and display all previous messages from a conversation when the user opens the chat interface.

## Implementation Details

### Backend Changes

1. **New API Endpoint**: `GET /api/v1/conversations/{conversation_id}/history`
   - Fetches conversation history from LangGraph checkpoints
   - Returns all messages in the conversation
   - Location: `app/api/routes.py`

2. **New Schemas**:
   - `ConversationHistoryItem`: Represents a single message in history
   - `ConversationHistoryResponse`: Response containing conversation ID and messages
   - Location: `app/api/schemas.py`

### Frontend Changes

1. **Service Layer** (`frontend/src/services/chatService.ts`):
   - Added `getConversationHistory()` function to fetch history from backend

2. **Custom Hook** (`frontend/src/hooks/useChat.ts`):
   - Uses React Query to fetch conversation history when `conversationId` is available
   - Automatically loads history into messages state
   - Refetches history after sending a new message to stay in sync

3. **UI Components**:
   - `MessageList`: Shows "Loading conversation history..." when fetching
   - `ChatContainer`: Passes loading state to MessageList

## How It Works

1. **On Page Load**:
   - Frontend gets or creates a `conversationId` from localStorage
   - React Query automatically fetches conversation history for that ID
   - History is loaded into the messages state
   - Messages are displayed in the chat interface

2. **When Sending a Message**:
   - User sends a message
   - Backend processes it and saves to checkpoint
   - After response, frontend refetches history to get updated state
   - UI updates with new messages

3. **Data Flow**:
   ```
   User opens app
   → Get conversationId from localStorage
   → Fetch history from backend (GET /conversations/{id}/history)
   → Backend reads from LangGraph checkpoint
   → Return conversation_history array
   → Frontend displays messages
   ```

## API Endpoint

### GET /api/v1/conversations/{conversation_id}/history

**Request:**
- Path parameter: `conversation_id` (string)

**Response:**
```json
{
  "conversation_id": "conv-12345",
  "messages": [
    {
      "role": "user",
      "content": "Where is my order?"
    },
    {
      "role": "assistant",
      "content": "Your order is currently in transit..."
    }
  ]
}
```

## Benefits

1. **Persistent Conversations**: Users can see their previous conversation when returning
2. **Context Preservation**: Full conversation context is maintained
3. **Better UX**: No need to re-explain previous questions
4. **Automatic Sync**: History stays in sync with backend state

## Technical Notes

- History is stored in LangGraph's checkpoint system (MemorySaver)
- Each conversation is identified by `thread_id` (conversation_id)
- Messages are stored as `List[Dict[str, str]]` with `role` and `content` keys
- Frontend uses React Query for caching and automatic refetching
- History is refetched after each message to ensure consistency

## Future Enhancements

1. Add timestamps to messages (currently using current time)
2. Pagination for very long conversations
3. Search functionality within conversation history
4. Export conversation history
5. Delete conversation history option
