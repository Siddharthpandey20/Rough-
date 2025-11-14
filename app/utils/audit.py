"""
Audit logging utilities
"""

import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

from app.models.audit import AuditRecord, AuditActor, AuditAction
from app.core.database import get_audit_db

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logging service for compliance and traceability"""
    
    @staticmethod
    def compute_record_hash(record_data: Dict) -> str:
        """Compute SHA-256 hash of record for tamper detection"""
        # Create deterministic string representation
        hash_input = json.dumps(record_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    @staticmethod
    def log_action(
        db: Session,
        actor: AuditActor,
        action: AuditAction,
        user_id: Optional[int] = None,
        user_type: Optional[str] = None,
        transaction_id: Optional[int] = None,
        reason: Optional[Dict] = None,
        related_context: Optional[Dict] = None,
        outcome: Optional[str] = None,
        confidence: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> AuditRecord:
        """
        Create audit log entry
        
        Args:
            actor: Who performed the action (system/user/admin)
            action: What action was performed
            user_id: User ID involved
            user_type: 'consumer' or 'business'
            transaction_id: Transaction ID if applicable
            reason: Structured reasoning {component, score, evidence}
            related_context: Snapshot of data used (encrypted if sensitive)
            outcome: Result of the action
            confidence: Confidence score (0-1)
            ip_address: IP address of actor
            user_agent: User agent string
            device_id: Device identifier
            metadata: Additional metadata
        """
        try:
            # Get previous record hash for chain
            previous_record = db.query(AuditRecord).order_by(AuditRecord.id.desc()).first()
            previous_hash = previous_record.record_hash if previous_record else None
            
            # Create record data for hashing
            record_data = {
                "user_id": user_id,
                "user_type": user_type,
                "transaction_id": transaction_id,
                "actor": actor.value,
                "action": action.value,
                "outcome": outcome,
                "confidence": confidence,
                "timestamp": datetime.utcnow().isoformat(),
                "previous_hash": previous_hash
            }
            
            # Compute current record hash
            record_hash = AuditLogger.compute_record_hash(record_data)
            
            # Create audit record
            audit_record = AuditRecord(
                user_id=user_id,
                user_type=user_type,
                transaction_id=transaction_id,
                actor=actor,
                action=action,
                reason=reason or {},
                related_context=related_context or {},
                outcome=outcome,
                confidence=confidence,
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=device_id,
                previous_record_hash=previous_hash,
                record_hash=record_hash,
                metadata=metadata or {}
            )
            
            db.add(audit_record)
            db.commit()
            db.refresh(audit_record)
            
            logger.info(f"Audit log created: {action.value} by {actor.value} for user {user_id}")
            
            return audit_record
        
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def log_anomaly_detection(
        db: Session,
        transaction_id: int,
        user_id: int,
        user_type: str,
        anomaly_score: float,
        isolation_forest_score: float,
        sigma_deviation: float,
        evidence: Dict,
        flagged: bool
    ):
        """Log anomaly detection event"""
        reason = {
            "component": "anomaly_detection",
            "anomaly_score": anomaly_score,
            "isolation_forest_score": isolation_forest_score,
            "sigma_deviation": sigma_deviation,
            "evidence": evidence
        }
        
        return AuditLogger.log_action(
            db=db,
            actor=AuditActor.SYSTEM,
            action=AuditAction.ANOMALY_DETECTED,
            user_id=user_id,
            user_type=user_type,
            transaction_id=transaction_id,
            reason=reason,
            outcome="flagged" if flagged else "normal",
            confidence=anomaly_score
        )
    
    @staticmethod
    def log_classification(
        db: Session,
        transaction_id: int,
        user_id: int,
        user_type: str,
        category: str,
        confidence: float,
        model_output: Dict
    ):
        """Log transaction classification event"""
        reason = {
            "component": "classifier",
            "category": category,
            "model_output": model_output
        }
        
        return AuditLogger.log_action(
            db=db,
            actor=AuditActor.SYSTEM,
            action=AuditAction.CLASSIFIED,
            user_id=user_id,
            user_type=user_type,
            transaction_id=transaction_id,
            reason=reason,
            outcome=category,
            confidence=confidence
        )
    
    @staticmethod
    def log_user_confirmation(
        db: Session,
        transaction_id: int,
        user_id: int,
        user_type: str,
        confirmed: bool,
        corrected_category: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log user confirmation/rejection of flagged transaction"""
        outcome = "confirmed" if confirmed else "rejected"
        reason = {
            "component": "hitl",
            "user_decision": outcome,
            "corrected_category": corrected_category
        }
        
        return AuditLogger.log_action(
            db=db,
            actor=AuditActor.USER,
            action=AuditAction.HITL_REVIEW,
            user_id=user_id,
            user_type=user_type,
            transaction_id=transaction_id,
            reason=reason,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_rag_query(
        db: Session,
        user_id: int,
        user_type: str,
        query: str,
        intent: str,
        retrieved_docs: list,
        response: str,
        confidence: float
    ):
        """Log RAG chatbot query and response"""
        reason = {
            "component": "rag",
            "query": query,
            "intent": intent,
            "retrieved_doc_count": len(retrieved_docs)
        }
        
        related_context = {
            "retrieved_docs": retrieved_docs,
            "response_summary": response[:200]  # First 200 chars
        }
        
        return AuditLogger.log_action(
            db=db,
            actor=AuditActor.USER,
            action=AuditAction.RAG_QUERY,
            user_id=user_id,
            user_type=user_type,
            reason=reason,
            related_context=related_context,
            outcome="success",
            confidence=confidence
        )
