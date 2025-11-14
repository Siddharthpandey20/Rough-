"""Database models initialization"""

# Import all models in the correct order to resolve relationships
# Order matters: import base models first, then dependent models

from app.models.user import UserConsumer, UserBusiness, UserType
from app.models.merchant import Merchant
from app.models.source import Source
from app.models.transaction import Transaction, SourceType, PaymentChannel
from app.models.pattern import Pattern
from app.models.chat import ChatSession, ChatMessage, ChatMemory
from app.models.rag import RAGIndex
from app.models.audit import AuditRecord, AuditActor, AuditAction

__all__ = [
    # User models
    "UserConsumer",
    "UserBusiness",
    "UserType",
    # Merchant
    "Merchant",
    # Source
    "Source",
    # Transaction
    "Transaction",
    "SourceType",
    "PaymentChannel",
    # Pattern
    "Pattern",
    # Chat
    "ChatSession",
    "ChatMessage",
    "ChatMemory",
    # RAG
    "RAGIndex",
    # Audit
    "AuditRecord",
    "AuditActor",
    "AuditAction",
]
