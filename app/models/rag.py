"""
RAG Index Model - tracks indexed documents for RAG
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class RAGIndex(Base):
    """RAGIndex Model - metadata for vector store documents"""
    __tablename__ = "rag_indices"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Document identification
    doc_id = Column(String, unique=True, index=True, nullable=False)  # UUID
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    
    # User reference (for user-specific retrieval)
    user_consumer_id = Column(Integer, ForeignKey("users_consumer.id"), nullable=True)
    user_business_id = Column(Integer, ForeignKey("users_business.id"), nullable=True)
    
    # Document content
    doc_type = Column(String, nullable=False)  # 'transaction', 'summary', 'audit'
    doc_summary = Column(Text, nullable=True)  # Human-readable summary
    doc_content = Column(Text, nullable=False)  # Full text for embedding
    
    # Vector store reference
    embedding_vector_ref = Column(String, nullable=True)  # Reference to vector in FAISS/Chroma
    embedding_model = Column(String, nullable=True)  # Model used for embedding
    
    # Additional context (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    index_metadata = Column(JSON, default=dict)  # Additional context
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
