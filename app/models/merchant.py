"""
Merchant Model - tracks merchants/vendors
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Merchant(Base):
    """Merchant Model - normalized merchant/vendor information"""
    __tablename__ = "merchants"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference (each user has their own merchant normalizations)
    user_consumer_id = Column(Integer, ForeignKey("users_consumer.id"), nullable=True)
    user_business_id = Column(Integer, ForeignKey("users_business.id"), nullable=True)
    
    # Merchant details
    name_normalized = Column(String, nullable=False, index=True)
    name_variants = Column(JSON, default=list)  # List of different name spellings
    
    # UPI/Bank details (encrypted)
    upi_id = Column(String, nullable=True)  # Encrypted
    bank_account = Column(String, nullable=True)  # Encrypted
    ifsc = Column(String, nullable=True)  # Encrypted
    
    # Statistics
    total_tx_count = Column(Integer, default=0)
    avg_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    freq_rank = Column(Integer, default=0)  # Ranking by frequency
    
    # Temporal
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    
    # Metadata
    tags = Column(JSON, default=list)  # e.g., ['frequent', 'high_cost', 'recurring']
    last_3_images_hash = Column(JSON, default=list)  # For similarity detection
    notes = Column(Text, nullable=True)
    
    # E2EE
    encrypted_fields = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_consumer = relationship("UserConsumer", back_populates="merchants", foreign_keys=[user_consumer_id])
    user_business = relationship("UserBusiness", back_populates="merchants", foreign_keys=[user_business_id])
    transactions = relationship("Transaction", back_populates="merchant")
