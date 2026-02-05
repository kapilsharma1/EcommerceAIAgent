"""Conversation service for managing conversations."""
from typing import Optional, List
from langsmith import traceable
from app.models.domain import Conversation
from app.conversations.repository import ConversationRepository
from sqlalchemy.ext.asyncio import AsyncSession


class ConversationService:
    """Service for conversation management."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize conversation service.
        
        Args:
            session: Database session
        """
        self.repository = ConversationRepository(session)
    
    @traceable(name="get_or_create_conversation")
    async def get_or_create_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        last_message: Optional[str] = None,
    ) -> Conversation:
        """
        Get existing conversation or create a new one.
        
        Args:
            conversation_id: Conversation ID
            title: Conversation title (used if creating new)
            last_message: Last message preview (optional)
            
        Returns:
            Conversation
        """
        return await self.repository.get_or_create_conversation(
            conversation_id=conversation_id,
            title=title,
            last_message=last_message,
        )
    
    @traceable(name="update_conversation")
    async def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        last_message: Optional[str] = None,
    ) -> Optional[Conversation]:
        """
        Update conversation.
        
        Args:
            conversation_id: Conversation ID
            title: New title (optional)
            last_message: New last message (optional)
            
        Returns:
            Updated Conversation if found, None otherwise
        """
        return await self.repository.update_conversation(
            conversation_id=conversation_id,
            title=title,
            last_message=last_message,
        )
    
    @traceable(name="get_conversation")
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation if found, None otherwise
        """
        return await self.repository.get_conversation(conversation_id)
    
    @traceable(name="list_conversations")
    async def list_conversations(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Conversation]:
        """
        List all conversations sorted by updated_at descending.
        
        Args:
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip
            
        Returns:
            List of Conversations
        """
        return await self.repository.list_conversations(limit=limit, offset=offset)
    
    @traceable(name="delete_conversation")
    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete_conversation(conversation_id)
    
    async def delete_all_conversations(self) -> int:
        """
        Delete all conversations from database.
        
        TEMPORARY FIX: Used to clear conversations on startup for MemorySaver sync.
        
        MIGRATION TO POSTGRESSAVER:
        - This method should be REMOVED when migrating to PostgresSaver
        - No longer needed once checkpoints are persisted in PostgreSQL
        
        Returns:
            Number of conversations deleted
        """
        return await self.repository.delete_all_conversations()