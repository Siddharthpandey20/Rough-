"""Transaction endpoints - stub implementation"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.utils.auth import get_current_user
from app.models.transaction import Transaction, SourceType, PaymentChannel
from app.models.source import Source
from app.models.merchant import Merchant

router = APIRouter()

@router.get("/")
async def get_transactions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(100, le=1000),
    offset: int = 0,
    flagged_only: bool = False
):
    """Get user transactions with filters"""
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    # Build query based on user type
    if user_type == "consumer":
        query = db.query(Transaction).filter(Transaction.user_consumer_id == user.id)
    else:
        query = db.query(Transaction).filter(Transaction.user_business_id == user.id)
    
    if flagged_only:
        query = query.filter(Transaction.flagged == True)
    
    transactions = query.offset(offset).limit(limit).all()
    total = query.count()
    
    return {
        "transactions": transactions,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/stats")
async def get_transaction_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze")
):
    """
    Get transaction statistics and insights
    
    **Purpose**: Provides aggregated analytics to help users understand:
    - Total spending and income
    - Category-wise breakdowns
    - Top merchants
    - Spending trends
    - Anomaly counts
    
    **AI Integration**: Stats feed into anomaly detection by establishing baselines
    """
    from sqlalchemy import func
    from datetime import timedelta
    
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    # Date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Build base query
    if user_type == "consumer":
        base_query = db.query(Transaction).filter(
            Transaction.user_consumer_id == user.id,
            Transaction.date >= cutoff_date
        )
    else:
        base_query = db.query(Transaction).filter(
            Transaction.user_business_id == user.id,
            Transaction.date >= cutoff_date
        )
    
    # Total transactions
    total_count = base_query.count()
    
    # Total amount (sum of all transactions)
    total_amount = base_query.with_entities(
        func.sum(Transaction.amount)
    ).scalar() or 0.0
    
    # Category breakdown
    category_stats = base_query.with_entities(
        Transaction.category,
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('total')
    ).group_by(Transaction.category).all()
    
    categories = [
        {
            "category": cat,
            "count": count,
            "total": float(total),
            "percentage": (float(total) / total_amount * 100) if total_amount > 0 else 0
        }
        for cat, count, total in category_stats
    ]
    
    # Top merchants
    top_merchants = base_query.with_entities(
        Transaction.merchant_name_raw,
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('total')
    ).group_by(Transaction.merchant_name_raw)\
     .order_by(func.sum(Transaction.amount).desc())\
     .limit(10).all()
    
    merchants = [
        {
            "merchant": merchant,
            "transaction_count": count,
            "total_spent": float(total)
        }
        for merchant, count, total in top_merchants
    ]
    
    # Flagged transactions (anomalies)
    flagged_count = base_query.filter(Transaction.flagged == True).count()
    confirmed_count = base_query.filter(Transaction.confirmed == True).count()
    
    # Payment channel breakdown
    channel_stats = base_query.with_entities(
        Transaction.payment_channel,
        func.count(Transaction.id).label('count')
    ).group_by(Transaction.payment_channel).all()
    
    channels = {
        str(channel.value): count 
        for channel, count in channel_stats
    }
    
    # Average transaction amount
    avg_amount = total_amount / total_count if total_count > 0 else 0
    
    return {
        "period_days": days,
        "total_transactions": total_count,
        "total_amount": round(total_amount, 2),
        "average_amount": round(avg_amount, 2),
        "flagged_count": flagged_count,
        "confirmed_count": confirmed_count,
        "unconfirmed_count": total_count - confirmed_count,
        "categories": sorted(categories, key=lambda x: x['total'], reverse=True),
        "top_merchants": merchants,
        "payment_channels": channels,
        "purpose": {
            "description": "Statistics provide baseline data for AI anomaly detection",
            "features": [
                "Category spending patterns help identify unusual transactions",
                "Merchant frequency helps detect first-time or rare vendors",
                "Average amounts establish normal spending ranges",
                "Payment channel patterns detect unusual payment methods"
            ]
        }
    }

@router.get("/{transaction_id}")
async def get_transaction(
    transaction_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific transaction"""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@router.post("/{transaction_id}/confirm")
async def confirm_transaction(
    transaction_id: int,
    confirmed: bool,
    notes: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Confirm or reject a transaction (Human-in-the-Loop)
    
    **Purpose**: 
    - Allows users to verify AI classifications and anomaly detections
    - Feeds back into AI learning (future enhancement)
    - Provides audit trail for flagged transactions
    
    **AI Integration**:
    - Confirmation data can retrain classification models
    - Helps calibrate anomaly detection thresholds
    - Builds user-specific spending patterns
    """
    from app.utils.audit import log_audit
    
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    # Get transaction
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Verify ownership
    if user_type == "consumer" and transaction.user_consumer_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    elif user_type == "business" and transaction.user_business_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update transaction
    old_confirmed = transaction.confirmed
    old_flagged = transaction.flagged
    
    transaction.confirmed = confirmed
    
    if not confirmed:
        # If rejecting, flag it
        transaction.flagged = True
    
    # Add notes to parsed_fields
    if notes:
        if not transaction.parsed_fields:
            transaction.parsed_fields = {}
        transaction.parsed_fields['user_notes'] = notes
        transaction.parsed_fields['confirmation_date'] = datetime.utcnow().isoformat()
    
    db.commit()
    
    # Log audit trail
    try:
        log_audit(
            db=db,
            user_id=user.id,
            user_type=user_type,
            transaction_id=transaction_id,
            action="CONFIRMED" if confirmed else "REJECTED",
            actor="user",
            reason={
                "previous_state": {
                    "confirmed": old_confirmed,
                    "flagged": old_flagged
                },
                "new_state": {
                    "confirmed": confirmed,
                    "flagged": transaction.flagged
                },
                "user_notes": notes
            },
            outcome="success"
        )
    except Exception as e:
        # Don't fail the request if audit logging fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Audit logging failed: {e}")
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "confirmed": confirmed,
        "flagged": transaction.flagged,
        "message": "Transaction confirmed" if confirmed else "Transaction rejected",
        "ai_benefit": "Your feedback helps improve AI accuracy and personalize anomaly detection"
    }

