"""
Audit Model - comprehensive audit trail (separate schema)
"""

from sqlalchemy import Column, Float, Integer, String, DateTime, JSON, Text, Enum as SQLEnum
from datetime import datetime
import enum

from app.core.database import AuditBase


class AuditActor(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ADMIN = "admin"


class AuditAction(str, enum.Enum):
    FLAGGED = "flagged"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CLASSIFIED = "classified"
    RATIONALE_GENERATED = "rationale_generated"
    RAG_QUERY = "rag_query"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTERED = "user_registered"
    DATA_INGESTED = "data_ingested"
    PATTERN_UPDATED = "pattern_updated"
    ANOMALY_DETECTED = "anomaly_detected"
    HITL_REVIEW = "hitl_review"
    CATEGORY_CHANGED = "category_changed"
    MERCHANT_MERGED = "merchant_merged"


class AuditRecord(AuditBase):
    """AuditRecord Model - tamper-proof audit trail"""
    __tablename__ = "audit_records"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Subject identification
    user_id = Column(Integer, nullable=True, index=True)
    user_type = Column(String, nullable=True)  # 'consumer' or 'business'
    transaction_id = Column(Integer, nullable=True, index=True)
    
    # Action details
    actor = Column(SQLEnum(AuditActor), nullable=False)  # Who made the decision
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)  # What was done
    
    # Reasoning and evidence
    reason = Column(JSON, nullable=True)  # Structured: {component, score, evidence}
    related_context = Column(JSON, nullable=True)  # Snapshot of data used (encrypted)
    
    # Additional details
    outcome = Column(String, nullable=True)  # Result of action
    confidence = Column(Float, nullable=True)  # Confidence score
    
    # IP and device tracking
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    
    # Tamper detection
    previous_record_hash = Column(String, nullable=True)
    record_hash = Column(String, nullable=True)  # Hash of this record
    
    # Timestamp (immutable)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    audit_metadata = Column(JSON, default=dict)
