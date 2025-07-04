from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .base import BaseRepository
from ..database.models import Conversation, Message

class ChatRepository:    
    def __init__(self, db: Session):
        self.db = db
        self.conversation_repo = BaseRepository(Conversation, db)
        self.message_repo = BaseRepository(Message, db)
    
    # Conversation operations
    def create_conversation(self, title: str = "New Conversation") -> Conversation:
        """Create a new conversation"""
        return self.conversation_repo.create(title=title)
    
    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID"""
        return self.conversation_repo.get(conversation_id)
    
    def get_conversations(self, skip: int = 0, limit: int = 50) -> List[Conversation]:
        """Get all conversations ordered by most recent"""
        return (self.db.query(Conversation)
                .order_by(desc(Conversation.updated_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def update_conversation_title(self, conversation_id: int, title: str) -> Optional[Conversation]:
        """Update conversation title"""
        return self.conversation_repo.update(conversation_id, title=title)
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation and all its messages"""
        return self.conversation_repo.delete(conversation_id)
    
    # Message operations
    def add_message(self, conversation_id: int, role: str, content: str) -> Message:
        """Add a message to a conversation"""
        message = self.message_repo.create(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        
        self.conversation_repo.update(conversation_id, updated_at=message.timestamp)
        
        return message
    
    def get_conversation_messages(self, conversation_id: int) -> List[Message]:
        """Get all messages for a conversation"""
        return (self.db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.timestamp)
                .all())
    
    def get_recent_messages(self, conversation_id: int, limit: int = 10) -> List[Message]:
        """Get recent messages for a conversation"""
        return (self.db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(desc(Message.timestamp))
                .limit(limit)
                .all())
    
    def clear_conversation_messages(self, conversation_id: int) -> bool:
        """Clear all messages from a conversation"""
        deleted_count = (self.db.query(Message)
                        .filter(Message.conversation_id == conversation_id)
                        .delete())
        self.db.commit()
        return deleted_count > 0
    
    def get_conversation_with_messages(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get conversation with all its messages"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        
        messages = self.get_conversation_messages(conversation_id)
        
        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": [msg.to_dict() for msg in messages]
        }
    
    def get_or_create_conversation(self, conversation_id: Optional[int] = None) -> Conversation:
        """Get existing conversation or create a new one"""
        if conversation_id:
            conversation = self.get_conversation(conversation_id)
            if conversation:
                return conversation
        
        return self.create_conversation()
    
    def search_conversations(self, search_term: str, limit: int = 20) -> List[Conversation]:
        """Search conversations by title or message content"""
        return (self.db.query(Conversation)
                .filter(Conversation.title.contains(search_term))
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
                .all()) 