"""Conversation repository for database operations."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc
from app.models.database import ConversationDB
from app.models.domain import Conversation


class ConversationRepository:
    """Repository for conversation database operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize conversation repository.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def create_conversation(
        self,
        conversation_id: str,
        title: str,
        last_message: Optional[str] = None,
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            title: Conversation title
            last_message: Last message preview (optional)
            
        Returns:
            Created Conversation
        """
        conversation_db = ConversationDB(
            conversation_id=conversation_id,
            title=title,
            last_message=last_message,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.session.add(conversation_db)
        await self.session.commit()
        await self.session.refresh(conversation_db)
        
        return self._db_to_domain(conversation_db)
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation if found, None otherwise
        """
        result = await self.session.execute(
            select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
        )
        conversation_db = result.scalar_one_or_none()
        
        if not conversation_db:
            return None
        
        return self._db_to_domain(conversation_db)
    
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
        update_values = {"updated_at": datetime.utcnow()}
        
        if title is not None:
            update_values["title"] = title
        
        if last_message is not None:
            # Truncate last_message to 500 characters
            update_values["last_message"] = last_message[:500] if len(last_message) > 500 else last_message
        
        await self.session.execute(
            update(ConversationDB)
            .where(ConversationDB.conversation_id == conversation_id)
            .values(**update_values)
        )
        await self.session.commit()
        
        return await self.get_conversation(conversation_id)
    
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
        existing = await self.get_conversation(conversation_id)
        
        if existing:
            # Update if last_message provided
            if last_message is not None:
                return await self.update_conversation(conversation_id, last_message=last_message)
            return existing
        
        # Create new conversation
        default_title = title or f"Conversation {conversation_id[:8]}"
        return await self.create_conversation(conversation_id, default_title, last_message)
    
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
        result = await self.session.execute(
            select(ConversationDB)
            .order_by(desc(ConversationDB.updated_at))
            .limit(limit)
            .offset(offset)
        )
        conversations_db = result.scalars().all()
        
        return [self._db_to_domain(conv_db) for conv_db in conversations_db]
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
        )
        await self.session.commit()
        
        return result.rowcount > 0
    
    def _db_to_domain(self, conversation_db: ConversationDB) -> Conversation:
        """Convert database model to domain model."""
        return Conversation(
            conversation_id=conversation_db.conversation_id,
            title=conversation_db.title,
            last_message=conversation_db.last_message,
            created_at=conversation_db.created_at,
            updated_at=conversation_db.updated_at,
        )
