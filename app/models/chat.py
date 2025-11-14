"""
Chat Models - ChatSession and ChatMemory
"""

from sqlalchemy import Column,Float, Integer, String, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class ChatSession(Base):
    """ChatSession Model - tracks conversation sessions"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference
    user_consumer_id = Column(Integer, ForeignKey("users_consumer.id"), nullable=True)
    user_business_id = Column(Integer, ForeignKey("users_business.id"), nullable=True)
    
    # Session metadata
    session_metadata = Column(JSON, default=dict)  # {locale, device, started_at}
    
    # Ephemeral memory (session-specific, temporary)
    ephemeral_memory = Column(JSON, default=dict)  # Short-term facts like "user said name is X"
    
    # Persistent memory references
    persistent_memory_refs = Column(JSON, default=list)  # List of ChatMemory IDs
    
    # Session state
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    last_interaction_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Relationships
    user_consumer = relationship("UserConsumer", back_populates="chat_sessions", foreign_keys=[user_consumer_id])
    user_business = relationship("UserBusiness", back_populates="chat_sessions", foreign_keys=[user_business_id])
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """ChatMessage Model - individual messages in a session"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    
    # Message details
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    
    # Metadata
    intent = Column(String, nullable=True)  # Classified intent
    retrieved_docs = Column(JSON, default=list)  # Documents used for RAG
    provenance = Column(JSON, default=dict)  # Transaction IDs and confidence scores
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    session = relationship("ChatSession", back_populates="messages")


class ChatMemory(Base):
    """ChatMemory Model - persistent user facts across sessions"""
    __tablename__ = "chat_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference
    user_consumer_id = Column(Integer, ForeignKey("users_consumer.id"), nullable=True)
    user_business_id = Column(Integer, ForeignKey("users_business.id"), nullable=True)
    
    # Memory details
    key = Column(String, nullable=False, index=True)  # e.g., "preferred_name"
    value = Column(Text, nullable=False)
    source = Column(String, default="user")  # 'user' or 'derived'
    
    # Visibility and expiration
    visibility = Column(String, default="persistent")  # 'session-only' or 'persistent'
    expiration = Column(DateTime, nullable=True)
    
    # Metadata
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_consumer = relationship("UserConsumer", back_populates="chat_memories", foreign_keys=[user_consumer_id])
    user_business = relationship("UserBusiness", back_populates="chat_memories", foreign_keys=[user_business_id])
