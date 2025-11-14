"""
User Models - Consumer and Business Users
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class UserType(str, enum.Enum):
    CONSUMER = "consumer"
    BUSINESS = "business"


class UserConsumer(Base):
    """Consumer User Model"""
    __tablename__ = "users_consumer"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    
    # Settings
    timezone = Column(String, default="UTC")
    locale = Column(String, default="en")
    currency = Column(String, default="INR")
    
    # Preferences
    budget_preferences = Column(JSON, default=dict)
    personal_category_set = Column(JSON, default=list)  # User's custom categories
    
    # Consent flags
    consent_gmail_ingest = Column(Boolean, default=False)
    consent_whatsapp_ingest = Column(Boolean, default=False)
    consent_upi_ingest = Column(Boolean, default=False)
    consent_sms_ingest = Column(Boolean, default=False)
    
    # E2EE - Store wrapped master keys per device
    device_keys = Column(JSON, default=dict)  # {device_id: wrapped_master_key}
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user_consumer", lazy="dynamic")
    merchants = relationship("Merchant", back_populates="user_consumer", lazy="dynamic")
    patterns = relationship("Pattern", back_populates="user_consumer", lazy="dynamic")
    chat_sessions = relationship("ChatSession", back_populates="user_consumer", lazy="dynamic")
    chat_memories = relationship("ChatMemory", back_populates="user_consumer", lazy="dynamic")


class UserBusiness(Base):
    """Business User Model"""
    __tablename__ = "users_business"
    
    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, nullable=False)
    contact_person = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    
    # Business specific
    gstin = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    pos_integration = Column(Boolean, default=False)
    
    # Settings
    timezone = Column(String, default="UTC")
    locale = Column(String, default="en")
    currency = Column(String, default="INR")
    
    # Business preferences
    business_category_set = Column(JSON, default=list)
    expected_invoice_rules = Column(JSON, default=dict)  # Pre-registered recurring vendors
    
    # Consent flags
    consent_gmail_ingest = Column(Boolean, default=False)
    consent_whatsapp_ingest = Column(Boolean, default=False)
    consent_upi_ingest = Column(Boolean, default=False)
    consent_sms_ingest = Column(Boolean, default=False)
    
    # E2EE
    device_keys = Column(JSON, default=dict)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user_business", lazy="dynamic")
    merchants = relationship("Merchant", back_populates="user_business", lazy="dynamic")
    patterns = relationship("Pattern", back_populates="user_business", lazy="dynamic")
    chat_sessions = relationship("ChatSession", back_populates="user_business", lazy="dynamic", foreign_keys="ChatSession.user_business_id")
    chat_memories = relationship("ChatMemory", back_populates="user_business", lazy="dynamic", foreign_keys="ChatMemory.user_business_id")
