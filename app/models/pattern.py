"""
Pattern Model - stores learned spending patterns
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Pattern(Base):
    """Pattern Model - learned behavioral patterns per user and category"""
    __tablename__ = "patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference
    user_consumer_id = Column(Integer, ForeignKey("users_consumer.id"), nullable=True)
    user_business_id = Column(Integer, ForeignKey("users_business.id"), nullable=True)
    
    # Pattern specifics
    category_id = Column(String, nullable=False)  # Category this pattern applies to
    
    # Statistical measures
    avg_weekly_spend = Column(Float, default=0.0)
    avg_monthly_spend = Column(Float, default=0.0)
    std_weekly_spend = Column(Float, default=0.0)
    std_monthly_spend = Column(Float, default=0.0)
    
    # Temporal patterns
    recurring_interval_days = Column(Integer, nullable=True)  # e.g., 30 for monthly
    typical_days_of_week = Column(JSON, default=list)  # [0-6] where 0=Monday
    typical_time_of_day = Column(JSON, default=list)  # [hour_ranges]
    
    # Top merchants for this category
    top_merchants = Column(JSON, default=list)  # [{merchant_id, count, avg_amount}]
    
    # Anomaly detection thresholds (computed)
    upper_threshold_3sigma = Column(Float, nullable=True)
    upper_threshold_6sigma = Column(Float, nullable=True)
    
    # Sample count (for confidence)
    sample_count = Column(Integer, default=0)
    
    # Timestamps
    last_update = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_consumer = relationship("UserConsumer", back_populates="patterns", foreign_keys=[user_consumer_id])
    user_business = relationship("UserBusiness", back_populates="patterns", foreign_keys=[user_business_id])
