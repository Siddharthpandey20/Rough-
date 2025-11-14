"""
Source Model - tracks where transactions come from
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.models.transaction import SourceType


class Source(Base):
    """Source Model - origin of transaction data"""
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference (polymorphic - either consumer or business)
    user_consumer_id = Column(Integer, ForeignKey("users_consumer.id"), nullable=True)
    user_business_id = Column(Integer, ForeignKey("users_business.id"), nullable=True)
    
    # Source identification
    source_type = Column(SQLEnum(SourceType), nullable=False)
    external_id = Column(String, nullable=True)  # email-id, whatsapp-id, upi-ref, etc.
    
    # Raw data storage
    raw_path = Column(Text, nullable=True)  # Path to raw file/data
    raw_data_encrypted = Column(Text, nullable=True)  # Encrypted raw content (for small data)
    
    # Processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)
    
    # Metadata
    received_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="source")

