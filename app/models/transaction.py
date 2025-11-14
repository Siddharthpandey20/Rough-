"""
Transaction Model
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class UserType(str, enum.Enum):
    CONSUMER = "CONSUMER"
    BUSINESS = "BUSINESS"


class SourceType(str, enum.Enum):
    UPLOAD = "UPLOAD"
    MANUAL = "MANUAL"
    GMAIL = "GMAIL"
    WHATSAPP = "WHATSAPP"
    UPI_FEED = "UPI_FEED"
    SMS = "SMS"


class PaymentChannel(str, enum.Enum):
    UPI = "UPI"
    BANK_TRANSFER = "BANK_TRANSFER"
    NETBANKING = "NETBANKING"
    CARD = "CARD"
    CASH = "CASH"
    WALLET = "WALLET"
    IMPS = "IMPS"
    NEFT = "NEFT"
    UNKNOWN = "UNKNOWN"
    OTHER = "OTHER"


class Transaction(Base):
    """Transaction Model - stores all financial transactions"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference (polymorphic - either consumer or business)
    user_consumer_id = Column(Integer, ForeignKey("users_consumer.id"), nullable=True)
    user_business_id = Column(Integer, ForeignKey("users_business.id"), nullable=True)
    user_type = Column(SQLEnum(UserType), nullable=False)
    
    # Source and merchant
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=True)
    merchant_name_raw = Column(Text, nullable=True)  # Encrypted
    
    # Transaction details
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    date = Column(DateTime, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Invoice details
    invoice_no = Column(String, nullable=True)  # Encrypted
    payment_channel = Column(SQLEnum(PaymentChannel), nullable=False)
    source_type = Column(SQLEnum(SourceType), nullable=False)
    
    # OCR and parsing
    ocr_confidence = Column(Float, default=0.0)  # 0-1
    parsed_fields = Column(JSON, default=dict)  # Raw parser output (encrypted)
    
    # Classification
    category = Column(String, nullable=True)  # User-specific category
    classification_confidence = Column(Float, default=0.0)
    
    # Anomaly detection
    flagged = Column(Boolean, default=False)
    anomaly_score = Column(Float, nullable=True)
    anomaly_reason = Column(Text, nullable=True)
    
    # Human in the loop
    confirmed = Column(Boolean, nullable=True)  # None=pending, True=confirmed, False=rejected
    confirmed_by = Column(String, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    
    # E2EE - encrypted data and wrapped keys
    encrypted_data = Column(JSON, default=dict)  # {field: {ciphertext, nonce}}
    wrapped_deks = Column(JSON, default=dict)  # {device_id: wrapped_dek}
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_consumer = relationship("UserConsumer", back_populates="transactions", foreign_keys=[user_consumer_id])
    user_business = relationship("UserBusiness", back_populates="transactions", foreign_keys=[user_business_id])
    source = relationship("Source", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
