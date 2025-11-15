"""
n8n Webhook Endpoints
Dedicated endpoints for receiving parsed transaction data from n8n workflows
Unified endpoint for SMS, Gmail, and all transaction ingestion
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import datetime

from app.core.database import get_db
from app.utils.auth import get_current_user
from app.core.config import settings
from app.schemas.n8n_webhooks import N8nSMSWebhook, N8nWebhookResponse
from app.models.transaction import Transaction, PaymentChannel, SourceType as TransactionSourceType
from app.models.source import Source
from app.models.merchant import Merchant
from app.services.gemini_service import gemini_service
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Hardcoded Gmail user for automatic background processing
GMAIL_MONITOR_USER_ID = 1
GMAIL_MONITOR_EMAIL = "siddharth24102@iiitnr.edu.in"


@router.post("/sms", response_model=N8nWebhookResponse)
async def n8n_sms_webhook(
    webhook_data: N8nSMSWebhook,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    SMS-FW.com Transaction Webhook
    
    Receives forwarded SMS from SMS-FW.com service and processes payment-related messages only.
    
    **SMS-FW.com Format:**
    ```
    Forwarded using https://www.sms-fw.com
    From: 'SENDER_NAME' (+91XXXXXXXXXX)
    To: '#phonenumber-sim1'
    When: 2025-11-15 06:39:55
    ************
    [SMS TEXT]
    ```
    
    **Payment Detection:** Automatically filters non-payment SMS
    **Authentication:** Requires Bearer token
    """
    import re
    from datetime import datetime
    
    try:
        user = current_user["user"]
        user_type = current_user["user_type"]
        
        logger.info(f"SMS-FW webhook received from user {user.id}")
        
        # Check consent
        if not user.consent_sms_ingest:
            raise HTTPException(
                status_code=403,
                detail="SMS ingestion not enabled. Please enable consent first."
            )
        
        # Parse SMS-FW.com format
        raw_sms = webhook_data.raw_sms
        
        # Extract SMS body (text after ************)
        sms_body_match = re.search(r'\*{8,}[\r\n]+(.+)', raw_sms, re.DOTALL)
        sms_body = sms_body_match.group(1).strip() if sms_body_match else raw_sms
        
        # Extract sender info
        from_match = re.search(r"From: '(.+?)' \((.+?)\)", raw_sms)
        sender_name = from_match.group(1) if from_match else None
        sender_number = from_match.group(2) if from_match else None
        
        # Extract timestamp
        when_match = re.search(r"When: (.+?)[\r\n]", raw_sms)
        sms_timestamp = when_match.group(1) if when_match else None
        
        logger.info(f"Parsed SMS - Sender: {sender_name}, Body length: {len(sms_body)}")
        
        # Payment detection keywords
        payment_keywords = [
            r'\brs\.?\s*\d+', r'₹\s*\d+', r'inr\s*\d+',  # Currency
            r'debited?', r'credited?', r'paid', r'received', r'sent', r'transferred',  # Transaction verbs
            r'upi', r'imps', r'neft', r'rtgs',  # Payment methods
            r'a/?c\s*(?:no\.?)?\s*[x*]*\d+',  # Account number
            r'ref(?:erence)?(?:\s*no\.?)?[:\s]*\d+',  # Reference number
            r'txn', r'transaction', r'payment',  # Transaction keywords
        ]
        
        # Check if SMS contains payment-related content
        is_payment = any(re.search(pattern, sms_body, re.IGNORECASE) for pattern in payment_keywords)
        
        if not is_payment:
            logger.info(f"Non-payment SMS discarded from {sender_name}: {sms_body[:50]}...")
            return N8nWebhookResponse(
                success=True,
                transaction_id=None,
                source_id=None,
                message="Non-payment SMS filtered out",
                classification={"is_payment": False}
            )
        
        logger.info(f"Payment SMS detected from {sender_name}")
        
        # Parse transaction details using regex patterns
        amount = None
        merchant = None
        upi_id = None
        reference_number = None
        account_number = None
        transaction_type = "debit"  # Default
        balance = None
        
        # Amount extraction (Rs, ₹, INR)
        amount_patterns = [
            r'(?:rs\.?|₹|inr)\s*([0-9,]+\.?[0-9]*)',
            r'([0-9,]+\.?[0-9]*)\s*(?:rs\.?|₹|inr)',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, sms_body, re.IGNORECASE)
            if match:
                amount = float(match.group(1).replace(',', ''))
                break
        
        # Transaction type
        if re.search(r'credited?|received|deposited', sms_body, re.IGNORECASE):
            transaction_type = "credit"
        
        # UPI ID / VPA
        upi_match = re.search(r'(?:to|from)\s+(?:vpa\s+)?([a-z0-9._-]+@[a-z]+)', sms_body, re.IGNORECASE)
        if upi_match:
            upi_id = upi_match.group(1)
            merchant = upi_id.split('@')[0]  # Use UPI handle as merchant
        
        # Merchant name (if no UPI)
        if not merchant:
            merchant_patterns = [
                r'(?:to|at|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Capitalized words
                r'(?:to|at|from)\s+([A-Z0-9]+)',  # All caps
            ]
            for pattern in merchant_patterns:
                match = re.search(pattern, sms_body)
                if match:
                    merchant = match.group(1)
                    break
        
        # Reference number
        ref_patterns = [
            r'upi\s+ref(?:erence)?[:\s]*([0-9]+)',
            r'ref(?:erence)?(?:\s*no\.?)?[:\s]*([0-9]+)',
            r'txn[:\s]*([0-9]+)',
        ]
        for pattern in ref_patterns:
            match = re.search(pattern, sms_body, re.IGNORECASE)
            if match:
                reference_number = match.group(1)
                break
        
        # Account number (last 4 digits)
        acc_match = re.search(r'a/?c\s*(?:no\.?)?\s*[x*]*([0-9]{4})', sms_body, re.IGNORECASE)
        if acc_match:
            account_number = acc_match.group(1)
        
        # Balance
        balance_match = re.search(r'(?:bal|balance)[:\s]*(?:rs\.?|₹)?\s*([0-9,]+\.?[0-9]*)', sms_body, re.IGNORECASE)
        if balance_match:
            balance = float(balance_match.group(1).replace(',', ''))
        
        # Validation
        if not amount or amount <= 0:
            logger.warning(f"Could not extract valid amount from SMS: {sms_body[:100]}")
            raise HTTPException(status_code=400, detail="Could not extract transaction amount from SMS")
        
        if not merchant:
            merchant = sender_name or "Unknown Merchant"
        
        logger.info(f"Extracted: Amount=₹{amount}, Merchant={merchant}, UPI={upi_id}, Ref={reference_number}")
        
        # Create Source record
        source = Source(
            user_consumer_id=user.id if user_type == "consumer" else None,
            user_business_id=user.id if user_type == "business" else None,
            source_type=TransactionSourceType.SMS,
            processed=True,
            processed_at=datetime.utcnow(),
            received_at=datetime.utcnow()
        )
        db.add(source)
        db.flush()
        
        # Get or create merchant
        merchant_identifier = upi_id or merchant
        merchant_name = merchant[:255]
        
        merchant_obj = db.query(Merchant).filter(
            Merchant.name_normalized.ilike(f"%{merchant_identifier.lower().strip()}%")
        ).filter(
            (Merchant.user_consumer_id == user.id) if user_type == "consumer"
            else (Merchant.user_business_id == user.id)
        ).first()
        
        if not merchant_obj:
            merchant_obj = Merchant(
                user_consumer_id=user.id if user_type == "consumer" else None,
                user_business_id=user.id if user_type == "business" else None,
                name_normalized=merchant_identifier.lower().strip(),
                name_variants=[merchant_name] + ([upi_id] if upi_id else [])
            )
            db.add(merchant_obj)
            db.flush()
        
        # Determine payment channel
        payment_channel = PaymentChannel.UPI  # Default for SMS
        if re.search(r'\bimps\b', sms_body, re.IGNORECASE):
            payment_channel = PaymentChannel.IMPS
        elif re.search(r'\bneft\b', sms_body, re.IGNORECASE):
            payment_channel = PaymentChannel.NEFT
        elif re.search(r'\bcard\b', sms_body, re.IGNORECASE):
            payment_channel = PaymentChannel.CARD
        
        # Get user categories
        user_categories = settings.DEFAULT_CONSUMER_CATEGORIES if user_type == "consumer" else settings.DEFAULT_BUSINESS_CATEGORIES
        
        # Classify with AI
        category = "Unknown"
        classification_confidence = 0.0
        classification_reasoning = None
        
        try:
            classification = gemini_service.classify_transaction(
                merchant_name=merchant_name,
                amount=amount,
                parsed_fields={
                    "upi_id": upi_id,
                    "payment_method": "UPI",
                    "sender_id": sender_name,
                    "sms_body": sms_body[:200]
                },
                user_categories=user_categories
            )
            category = classification.get("category", "Unknown")
            classification_confidence = classification.get("confidence", 0.0)
            classification_reasoning = classification.get("reasoning")
        except Exception as e:
            logger.error(f"Classification failed: {e}")
        
        # Create transaction
        transaction = Transaction(
            user_consumer_id=user.id if user_type == "consumer" else None,
            user_business_id=user.id if user_type == "business" else None,
            user_type="CONSUMER" if user_type == "consumer" else "BUSINESS",
            source_id=source.id,
            merchant_id=merchant_obj.id,
            amount=amount,
            currency="INR",
            merchant_name_raw=merchant_name,
            category=category,
            date=datetime.utcnow(),
            payment_channel=payment_channel,
            source_type=TransactionSourceType.SMS,
            invoice_no=reference_number,
            confirmed=True,  # SMS alerts are confirmed
            classification_confidence=classification_confidence,
            ocr_confidence=1.0,
            parsed_fields={
                "upi_id": upi_id,
                "sender_id": sender_name,
                "sender_phone": sender_number,
                "sms_timestamp": sms_timestamp,
                "transaction_type": transaction_type,
                "account_number": account_number,
                "balance": balance,
                "classification_reasoning": classification_reasoning,
                "sms_fw_ingested": True,
                "raw_sms": sms_body
            }
        )
        db.add(transaction)
        db.flush()
        
        # Index for RAG
        try:
            rag_service.index_transaction(db, transaction, user.id, user_type)
            logger.info(f"Transaction {transaction.id} indexed for RAG")
        except Exception as rag_error:
            logger.error(f"RAG indexing failed: {rag_error}")
        
        db.commit()
        
        logger.info(f"✅ SMS transaction created: ID={transaction.id}, User={user.id}, Amount=₹{amount}")
        
        return N8nWebhookResponse(
            success=True,
            transaction_id=transaction.id,
            source_id=source.id,
            message=f"Transaction processed: {merchant_name} - ₹{amount}",
            classification={
                "category": category,
                "confidence": classification_confidence,
                "is_payment": True
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SMS-FW webhook error: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process SMS: {str(e)}")


@router.get("/health")
async def webhook_health():
    """
    Health check endpoint for n8n webhooks
    
    Use this to verify the webhook endpoints are accessible
    """
    from app.services.gmail_monitor_service import gmail_monitor
    
    return {
        "status": "healthy",
        "service": "LUMEN n8n Webhook Hub",
        "endpoints": {
            "sms": "/api/v1/n8n/sms",
            "gmail": "/api/v1/n8n/gmail"
        },
        "gmail_monitor": {
            "running": gmail_monitor.is_running,
            "monitored_email": GMAIL_MONITOR_EMAIL,
            "last_check": gmail_monitor.last_check_time.isoformat() if gmail_monitor.last_check_time else None
        },
        "sms_format": "SMS-FW.com forwarding service",
        "payment_filtering": "enabled",
        "authentication": "Bearer token required",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/gmail/start")
async def start_gmail_monitor(
    current_user=Depends(get_current_user)
):
    """
    Start Gmail background monitoring service
    
    This will continuously monitor siddharth24102@iiitnr.edu.in for transaction emails
    and save ALL found transactions to YOUR user account.
    
    The authenticated user calling this endpoint will receive all transactions.
    """
    from app.services.gmail_monitor_service import gmail_monitor
    
    try:
        user = current_user["user"]
        user_type = current_user["user_type"]
        
        if gmail_monitor.is_running:
            return {
                "success": True,
                "message": f"Gmail monitor already running - transactions going to User ID {gmail_monitor.current_user_id}",
                "monitored_email": GMAIL_MONITOR_EMAIL,
                "saving_to_user_id": gmail_monitor.current_user_id,
                "saving_to_user_type": gmail_monitor.current_user_type
            }
        
        # Start monitoring - ALL transactions will go to THIS USER
        logger.info(f"🚀 Starting Gmail monitor for User ID {user.id} ({user_type})")
        logger.info(f"📧 Monitoring: {GMAIL_MONITOR_EMAIL}")
        logger.info(f"💾 ALL transactions found will be saved to User ID {user.id}")
        
        gmail_monitor.start(user_id=user.id, user_type=user_type)
        
        return {
            "success": True,
            "message": f"Gmail monitor started! Checking {GMAIL_MONITOR_EMAIL}, ALL transactions will save to YOUR account (User ID {user.id})",
            "monitored_email": GMAIL_MONITOR_EMAIL,
            "saving_to_user_id": user.id,
            "saving_to_user_type": user_type,
            "check_interval_seconds": gmail_monitor.check_interval,
            "info": "Any transaction email in the monitored inbox will be added to your account"
        }
    
    except Exception as e:
        logger.error(f"Failed to start Gmail monitor: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start Gmail monitor: {str(e)}")


@router.post("/gmail/stop")
async def stop_gmail_monitor(
    current_user=Depends(get_current_user)
):
    """
    Stop Gmail background monitoring service
    """
    from app.services.gmail_monitor_service import gmail_monitor
    
    try:
        gmail_monitor.stop()
        
        return {
            "success": True,
            "message": "Gmail monitor stopped successfully"
        }
    
    except Exception as e:
        logger.error(f"Failed to stop Gmail monitor: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop Gmail monitor: {str(e)}")


@router.get("/gmail/status")
async def gmail_monitor_status():
    """
    Get Gmail monitor status
    
    Public endpoint to check if Gmail monitoring is active and which user is receiving transactions
    """
    from app.services.gmail_monitor_service import gmail_monitor
    import os
    from app.core.config import settings
    
    token_exists = os.path.exists(f"{settings.GMAIL_TOKEN_PATH}_{GMAIL_MONITOR_USER_ID}")
    
    return {
        "running": gmail_monitor.is_running,
        "monitored_email": GMAIL_MONITOR_EMAIL,
        "transactions_saving_to_user_id": gmail_monitor.current_user_id,
        "transactions_saving_to_user_type": gmail_monitor.current_user_type,
        "last_check": gmail_monitor.last_check_time.isoformat() if gmail_monitor.last_check_time else None,
        "check_interval_seconds": gmail_monitor.check_interval,
        "processed_messages_count": len(gmail_monitor.processed_message_ids),
        "authenticated": token_exists,
        "gmail_service_ready": gmail_monitor.gmail_service.service is not None,
        "info": f"All transactions found in {GMAIL_MONITOR_EMAIL} will be saved to User ID {gmail_monitor.current_user_id}" if gmail_monitor.current_user_id else "No user configured - call /api/v1/n8n/gmail/start to begin"
    }


@router.post("/gmail/check-now")
async def check_gmail_now(
    current_user=Depends(get_current_user)
):
    """
    Force immediate Gmail check
    
    Triggers an immediate check for new emails in siddharth24102@iiitnr.edu.in.
    Any transactions found will be saved to YOUR user account.
    """
    from app.services.gmail_monitor_service import gmail_monitor
    
    try:
        user = current_user["user"]
        user_type = current_user["user_type"]
        
        # If monitor not running, start it first with this user
        if not gmail_monitor.is_running:
            logger.info(f"Monitor not running - starting it for User ID {user.id}")
            gmail_monitor.start(user_id=user.id, user_type=user_type)
        else:
            # Monitor is running - update user if different
            if gmail_monitor.current_user_id != user.id:
                logger.warning(f"Monitor was configured for User ID {gmail_monitor.current_user_id}, updating to {user.id}")
                gmail_monitor.current_user_id = user.id
                gmail_monitor.current_user_type = user_type
        
        # Force immediate check
        logger.info(f"✅ Manual Gmail check triggered by User ID {user.id}")
        logger.info(f"📧 Checking: {GMAIL_MONITOR_EMAIL}")
        logger.info(f"💾 Transactions will be saved to: User ID {user.id} ({user_type})")
        
        gmail_monitor._check_new_emails()
        
        return {
            "success": True,
            "message": f"Email check completed! Any transactions found have been saved to your account (User ID {user.id})",
            "monitored_email": GMAIL_MONITOR_EMAIL,
            "saving_to_user_id": user.id,
            "last_check": gmail_monitor.last_check_time.isoformat() if gmail_monitor.last_check_time else None,
            "processed_messages_count": len(gmail_monitor.processed_message_ids)
        }
    
    except Exception as e:
        logger.error(f"Manual check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check Gmail: {str(e)}")


@router.post("/gmail/authenticate")
async def authenticate_gmail():
    """
    Force Gmail authentication
    
    Opens browser for OAuth flow if not already authenticated.
    Public endpoint for initial setup.
    """
    from app.services.gmail_monitor_service import gmail_monitor
    import os
    from app.core.config import settings
    
    try:
        token_path = f"{settings.GMAIL_TOKEN_PATH}_{GMAIL_MONITOR_USER_ID}"
        
        if os.path.exists(token_path):
            return {
                "success": True,
                "message": "Already authenticated",
                "token_exists": True,
                "monitored_email": GMAIL_MONITOR_EMAIL
            }
        
        logger.info("Starting Gmail authentication flow...")
        
        # Trigger authentication
        success = gmail_monitor._authenticate()
        
        if success:
            return {
                "success": True,
                "message": f"Gmail authenticated successfully for {GMAIL_MONITOR_EMAIL}",
                "token_exists": True,
                "monitored_email": GMAIL_MONITOR_EMAIL
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Authentication failed. Check that credentials/gmail_credentials.json exists and is valid."
            )
    
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")
