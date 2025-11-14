"""Anomaly detection endpoints - stub implementation"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.utils.auth import get_current_user
from app.models.transaction import Transaction

router = APIRouter()

@router.get("/flagged")
async def get_flagged_transactions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = 0,
    unconfirmed_only: bool = True
):
    """Get flagged transactions requiring review"""
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    if user_type == "consumer":
        query = db.query(Transaction).filter(
            Transaction.user_consumer_id == user.id,
            Transaction.flagged == True
        )
    else:
        query = db.query(Transaction).filter(
            Transaction.user_business_id == user.id,
            Transaction.flagged == True
        )
    
    if unconfirmed_only:
        query = query.filter(Transaction.confirmed == None)
    
    flagged = query.offset(offset).limit(limit).all()
    total = query.count()
    pending = query.filter(Transaction.confirmed == None).count()
    
    return {
        "flagged_transactions": flagged,
        "total": total,
        "pending_review": pending
    }

@router.get("/{transaction_id}/explain")
async def explain_anomaly(
    transaction_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get human-readable explanation for anomaly"""
    return {"message": "Anomaly explanation endpoint - to be implemented"}
