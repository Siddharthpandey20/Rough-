"""
Chat Schemas
"""

from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    session_id: int
    message_id: int
    response: str
    intent: Optional[str]
    provenance: Dict  # Transaction IDs and confidence scores
    retrieved_docs: List[Dict]
    timestamp: datetime


class ChatSessionCreate(BaseModel):
    session_metadata: Optional[Dict] = {}


class ChatSessionResponse(BaseModel):
    id: int
    session_metadata: Dict
    ephemeral_memory: Dict
    is_active: bool
    started_at: datetime
    last_interaction_at: datetime
    
    class Config:
        from_attributes = True


class ChatMemoryCreate(BaseModel):
    key: str
    value: str
    source: str = "user"
    visibility: str = "persistent"
    expiration: Optional[datetime] = None


class ChatMemoryResponse(BaseModel):
    id: int
    key: str
    value: str
    source: str
    visibility: str
    confidence: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ExactQueryRequest(BaseModel):
    """For exact transaction lookups"""
    merchant_name: Optional[str] = None
    amount: Optional[float] = None
    amount_tolerance: float = 0.02  # 2% tolerance
    date: Optional[datetime] = None
    date_tolerance_days: int = 1
    invoice_no: Optional[str] = None
