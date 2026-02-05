# Conversation List Feature

## Overview

This feature allows users to see all their previous conversations in a sidebar (similar to ChatGPT) and switch between them. Conversations are stored in PostgreSQL database.

## Implementation Details

### Backend Changes

1. **Database Model** (`app/models/database.py`):
   - Added `ConversationDB` model with fields:
     - `conversation_id` (primary key)
     - `title` (conversation title)
     - `last_message` (preview of last message)
     - `created_at` and `updated_at` timestamps

2. **Domain Model** (`app/models/domain.py`):
   - Added `Conversation` Pydantic model

3. **Repository** (`app/conversations/repository.py`):
   - `ConversationRepository` with CRUD operations
   - Methods: create, get, update, list, delete, get_or_create

4. **Service** (`app/conversations/service.py`):
   - `ConversationService` wrapping repository operations
   - LangSmith tracing support

5. **API Endpoints** (`app/api/routes.py`):
   - `GET /api/v1/conversations` - List all conversations
   - `DELETE /api/v1/conversations/{id}` - Delete a conversation
   - Updated `POST /api/v1/chat` to register/update conversations

6. **API Schemas** (`app/api/schemas.py`):
   - `ConversationListItem` - Single conversation item
   - `ConversationListResponse` - List response

7. **Database Migration** (`alembic/versions/add_conversations_table.py`):
   - Creates `conversations` table with indexes

### Frontend Changes

1. **Service** (`frontend/src/services/chatService.ts`):
   - `getConversationList()` - Fetch all conversations
   - `deleteConversation()` - Delete a conversation

2. **Components**:
   - `ConversationSidebar` - Sidebar showing all conversations
     - Lists all conversations sorted by updated_at
     - Shows title, last message preview, and relative time
     - Highlights current conversation
     - Delete button for each conversation
     - "New" button to create new conversation
     - Responsive (hidden on mobile, toggleable)

3. **Hooks** (`frontend/src/hooks/useConversation.ts`):
   - Added `switchConversation()` - Switch to a different conversation
   - Added `createNewConversation()` - Create a new conversation

4. **App Component** (`frontend/src/App.tsx`):
   - Integrated sidebar with toggle button
   - Mobile-responsive sidebar overlay

## Features

1. **Conversation List**: See all previous conversations in a sidebar
2. **Switch Conversations**: Click any conversation to switch to it
3. **New Conversation**: Create a new conversation with "+ New" button
4. **Delete Conversations**: Delete conversations with delete button
5. **Auto-Title**: First message becomes conversation title
6. **Last Message Preview**: Shows preview of last message
7. **Relative Timestamps**: Shows "2 hours ago" style timestamps
8. **Current Conversation Highlight**: Highlights active conversation
9. **Responsive Design**: Mobile-friendly with overlay sidebar

## Database Schema

```sql
CREATE TABLE conversations (
    conversation_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    last_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX ix_conversations_created_at ON conversations(created_at);
CREATE INDEX ix_conversations_updated_at ON conversations(updated_at);
```

## API Endpoints

### GET /api/v1/conversations

List all conversations sorted by updated_at descending.

**Query Parameters:**
- `limit` (optional, default: 100) - Maximum number to return
- `offset` (optional, default: 0) - Number to skip

**Response:**
```json
{
  "conversations": [
    {
      "conversation_id": "conv-12345",
      "title": "Where is my order?",
      "last_message": "Your order is currently in transit...",
      "created_at": "2026-01-06T10:00:00",
      "updated_at": "2026-01-06T12:00:00"
    }
  ]
}
```

### DELETE /api/v1/conversations/{conversation_id}

Delete a conversation.

**Response:**
```json
{
  "message": "Conversation deleted successfully"
}
```

## Usage

1. **View Conversations**: Sidebar automatically loads and displays all conversations
2. **Switch Conversation**: Click any conversation in the sidebar to switch to it
3. **New Conversation**: Click "+ New" button to start a new conversation
4. **Delete Conversation**: Click the trash icon on any conversation to delete it

## Migration

To apply the database migration:

```bash
alembic upgrade head
```

## Notes

- Conversations are automatically registered when a message is sent
- Title is auto-generated from the first message (first 50 characters)
- Last message is truncated to 500 characters
- Conversations are sorted by most recently updated first
- Frontend refetches conversation list every 30 seconds
- Deleting a conversation only removes it from the database, not from LangGraph checkpoints
