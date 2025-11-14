"""Ingestion endpoints - stub implementation"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
import os
import logging
from datetime import datetime

from app.core.database import get_db
from app.utils.auth import get_current_user
from app.core.config import settings
from app.services.ocr_service import ocr_service
from app.services.gemini_service import gemini_service
from app.services.rag_service import rag_service
from app.models.transaction import Transaction, PaymentChannel, SourceType as TransactionSourceType
from app.models.source import Source
from app.models.merchant import Merchant
from app.schemas.transaction import ConsumerManualTransaction, BusinessManualTransaction

# Map source type string to enum
SOURCE_TYPE_MAP = {
    "Upload": TransactionSourceType.UPLOAD,
    "UPLOAD": TransactionSourceType.UPLOAD,
    "Gmail": TransactionSourceType.GMAIL,
    "GMAIL": TransactionSourceType.GMAIL,
    "WhatsApp": TransactionSourceType.WHATSAPP,
    "WHATSAPP": TransactionSourceType.WHATSAPP,
}

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    source_type: str = Form("Upload"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process receipt/invoice"""
    try:
        user = current_user["user"]
        user_type = current_user["user_type"]
        
        # Validate file type
        if not file.content_type.startswith(("image/", "application/pdf")):
            raise HTTPException(status_code=400, detail="Only image and PDF files are supported")
        
        # Check file size
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")
        
        # Save file
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{user.id}_{timestamp}_{file.filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"File uploaded: {safe_filename} for user {user.id}")
        
        # OCR processing
        try:
            text, confidence = ocr_service.extract_text(file_path)
            parsed_data = ocr_service.parse_receipt(text)
            logger.info(f"OCR completed with confidence {confidence}")
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            # Continue with empty parsed data
            text = ""
            confidence = 0.0
            parsed_data = {}
        
        # Create Source record
        source_type_enum = SOURCE_TYPE_MAP.get(source_type, TransactionSourceType.UPLOAD)
        
        source = Source(
            user_consumer_id=user.id if user_type == "consumer" else None,
            user_business_id=user.id if user_type == "business" else None,
            source_type=source_type_enum,
            raw_path=file_path,
            raw_data_encrypted=None,  # TODO: Implement encryption
            processed=True,
            processed_at=datetime.utcnow()
        )
        db.add(source)
        db.flush()  # Get source.id
        
        # Create Transaction if we have enough data
        transaction_id = None
        classification = None
        if parsed_data.get("amount"):
            try:
                # Get user categories
                if user_type == "consumer":
                    user_categories = settings.DEFAULT_CONSUMER_CATEGORIES
                else:
                    user_categories = settings.DEFAULT_BUSINESS_CATEGORIES
                
                # Classify transaction
                classification = gemini_service.classify_transaction(
                    merchant_name=parsed_data.get("merchant_name", "Unknown"),
                    amount=float(parsed_data.get("amount", 0)),
                    parsed_fields=parsed_data,
                    user_categories=user_categories
                )
                
                # Get or create merchant
                merchant_name = parsed_data.get("merchant_name", "Unknown")[:255]
                merchant = db.query(Merchant).filter(
                    Merchant.name_normalized.ilike(f"%{merchant_name.lower().strip()}%")
                ).first()
                
                if not merchant:
                    merchant = Merchant(
                        user_consumer_id=user.id if user_type == "consumer" else None,
                        user_business_id=user.id if user_type == "business" else None,
                        name_normalized=merchant_name.lower().strip(),
                        name_variants=[merchant_name]
                    )
                    db.add(merchant)
                    db.flush()
                
                # Create transaction
                transaction = Transaction(
                    user_consumer_id=user.id if user_type == "consumer" else None,
                    user_business_id=user.id if user_type == "business" else None,
                    user_type="CONSUMER" if user_type == "consumer" else "BUSINESS",
                    source_id=source.id,
                    merchant_id=merchant.id,
                    amount=float(parsed_data.get("amount", 0)),
                    currency=parsed_data.get("currency", "INR"),
                    merchant_name_raw=merchant_name,
                    category=classification.get("category", "Unknown"),
                    date=parsed_data.get("date") or datetime.utcnow(),
                    payment_channel=PaymentChannel.UNKNOWN,
                    source_type=source_type_enum,
                    invoice_no=parsed_data.get("invoice_no"),
                    confirmed=False,
                    classification_confidence=classification.get("confidence", 0.0),
                    ocr_confidence=confidence,
                    parsed_fields={
                        "classification_reasoning": classification.get("reasoning"),
                        "items": parsed_data.get("items", []),
                        "tax": parsed_data.get("tax"),
                        "payment_method": parsed_data.get("payment_method")
                    }
                )
                db.add(transaction)
                db.flush()
                transaction_id = transaction.id
                
                # Index for RAG
                try:
                    rag_service.index_transaction(db, transaction, user.id, user_type)
                    logger.info(f"Transaction {transaction_id} indexed for RAG")
                except Exception as rag_error:
                    logger.error(f"RAG indexing failed: {rag_error}")
                    # Continue without RAG indexing
                
                logger.info(f"Transaction {transaction_id} created from upload")
            except Exception as e:
                logger.error(f"Transaction creation failed: {e}")
                # Continue without transaction
        
        db.commit()
        
        return {
            "status": "success",
            "source_id": source.id,
            "transaction_id": transaction_id,
            "ocr_confidence": confidence,
            "parsed_data": parsed_data,
            "classification": classification if transaction_id else None,
            "message": "File uploaded and processed successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload processing error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")

@router.get("/gmail/status")
async def gmail_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Gmail integration status"""
    from app.services.gmail_service import gmail_service
    
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    is_connected = gmail_service.is_authenticated(user.id)
    
    return {
        "connected": is_connected,
        "consent_enabled": user.consent_gmail_ingest,
        "message": "Gmail is connected" if is_connected else "Gmail not connected"
    }

@router.post("/gmail/connect")
async def connect_gmail(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect Gmail account and enable consent"""
    from app.services.gmail_service import gmail_service
    
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    try:
        # Authenticate with Gmail
        success = gmail_service.authenticate(user.id)
        
        if success:
            # Enable consent
            user.consent_gmail_ingest = True
            db.commit()
            
            return {
                "success": True,
                "message": "Gmail connected successfully! You can now sync transactions."
            }
        else:
            return {
                "success": False,
                "message": "Failed to connect Gmail. Please try again.",
                "oauth_url": gmail_service.get_oauth_url()
            }
    
    except Exception as e:
        logger.error(f"Gmail connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect Gmail: {str(e)}")

@router.post("/gmail/sync")
async def sync_gmail(
    days_back: int = 30,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync transactions from Gmail"""
    from app.services.gmail_service import gmail_service
    
    user = current_user["user"]
    user_type = current_user["user_type"]
    
    if not user.consent_gmail_ingest:
        raise HTTPException(status_code=403, detail="Gmail ingestion not enabled. Please connect Gmail first.")
    
    try:
        # Authenticate
        if not gmail_service.authenticate(user.id):
            raise HTTPException(status_code=401, detail="Gmail authentication failed")
        
        # Fetch emails
        transactions = gmail_service.fetch_transaction_emails(days_back=days_back)
        
        # Process and save transactions
        saved_count = 0
        for tx_data in transactions:
            try:
                # Create Source record
                source = Source(
                    user_consumer_id=user.id if user_type == "consumer" else None,
                    user_business_id=user.id if user_type == "business" else None,
                    source_type=TransactionSourceType.GMAIL,
                    processed=True,
                    processed_at=datetime.utcnow(),
                    received_at=tx_data.get('email_date', datetime.utcnow())
                )
                db.add(source)
                db.flush()
                
                # Get or create merchant
                merchant_name = tx_data.get('merchant', 'Unknown')[:255]
                merchant = db.query(Merchant).filter(
                    Merchant.name_normalized.ilike(f"%{merchant_name.lower().strip()}%")
                ).first()
                
                if not merchant:
                    merchant = Merchant(
                        user_consumer_id=user.id if user_type == "consumer" else None,
                        user_business_id=user.id if user_type == "business" else None,
                        name_normalized=merchant_name.lower().strip(),
                        name_variants=[merchant_name]
                    )
                    db.add(merchant)
                    db.flush()
                
                # Determine payment channel
                payment_method = tx_data.get('payment_method', 'UNKNOWN')
                channel_map = {
                    'UPI': PaymentChannel.UPI,
                    'CARD': PaymentChannel.CARD,
                    'IMPS': PaymentChannel.BANK_TRANSFER,
                    'NEFT': PaymentChannel.BANK_TRANSFER,
                    'NETBANKING': PaymentChannel.NETBANKING
                }
                payment_channel = channel_map.get(payment_method, PaymentChannel.UNKNOWN)
                
                # Get user categories
                if user_type == "consumer":
                    user_categories = settings.DEFAULT_CONSUMER_CATEGORIES
                else:
                    user_categories = settings.DEFAULT_BUSINESS_CATEGORIES
                
                # Classify
                classification = gemini_service.classify_transaction(
                    merchant_name=merchant_name,
                    amount=tx_data['amount'],
                    parsed_fields=tx_data,
                    user_categories=user_categories
                )
                
                # Create transaction
                transaction = Transaction(
                    user_consumer_id=user.id if user_type == "consumer" else None,
                    user_business_id=user.id if user_type == "business" else None,
                    user_type="CONSUMER" if user_type == "consumer" else "BUSINESS",
                    source_id=source.id,
                    merchant_id=merchant.id,
                    amount=tx_data['amount'],
                    currency="INR",
                    merchant_name_raw=merchant_name,
                    category=classification.get('category', 'Unknown'),
                    date=tx_data.get('email_date', datetime.utcnow()),
                    payment_channel=payment_channel,
                    source_type=TransactionSourceType.GMAIL,
                    invoice_no=tx_data.get('reference_number'),
                    confirmed=False,
                    classification_confidence=classification.get('confidence', 0.0),
                    parsed_fields={
                        'email_subject': tx_data.get('subject'),
                        'sender': tx_data.get('sender'),
                        'transaction_type': tx_data.get('transaction_type')
                    }
                )
                db.add(transaction)
                db.flush()
                
                # Index for RAG
                try:
                    rag_service.index_transaction(db, transaction, user.id, user_type)
                except:
                    pass
                
                saved_count += 1
            
            except Exception as e:
                logger.error(f"Error saving Gmail transaction: {e}")
                continue
        
        db.commit()
        
        return {
            "success": True,
            "fetched": len(transactions),
            "saved": saved_count,
            "message": f"Successfully synced {saved_count} transactions from Gmail"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gmail sync error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync Gmail: {str(e)}")

@router.post("/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db)
):
    """Twilio WhatsApp webhook"""
    from app.services.whatsapp_service import whatsapp_service
    
    try:
        logger.info(f"WhatsApp message from {From}: {Body}")
        
        # Parse incoming message
        parsed_data = whatsapp_service.parse_incoming_message(Body, From)
        
        if parsed_data:
            # This is a transaction message
            logger.info(f"Transaction detected from WhatsApp: {parsed_data}")
            
            # Send acknowledgment
            whatsapp_service.send_message(
                From,
                "✅ Transaction recorded!\n\n" +
                f"💰 Amount: ₹{parsed_data['amount']}\n" +
                f"🏪 Merchant: {parsed_data['merchant']}\n\n" +
                "View details in LUMEN app."
            )
            
            return {"status": "success", "message": "Transaction processed"}
        
        # Check if it's a command/reply
        reply_data = whatsapp_service.handle_user_reply(Body, From)
        
        if reply_data:
            action = reply_data['action']
            
            if action == 'greeting':
                whatsapp_service.send_message(
                    From,
                    "👋 Welcome to LUMEN!\n\n"
                    "I'm your financial assistant. I can help you:\n"
                    "📊 Track your expenses\n"
                    "💰 Monitor transactions\n"
                    "🔔 Get spending alerts\n\n"
                    "Send HELP to see available commands or forward your transaction SMS to me!"
                )
            elif action == 'help':
                whatsapp_service.send_help_message(From)
            elif action == 'get_summary':
                whatsapp_service.send_message(From, "📊 Summary feature coming soon!")
            
            return {"status": "success", "action": action}
        
        # Unknown message
        whatsapp_service.send_message(
            From,
            "🤖 I didn't understand that. Send HELP for available commands or forward transaction SMS to track them automatically."
        )
        
        return {"status": "success", "message": "Unknown command"}
    
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/manual/consumer")
async def add_consumer_transaction(
    transaction_data: ConsumerManualTransaction,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a manual transaction for CONSUMER users
    
    Perfect for logging:
    - Cash payments
    - Personal expenses
    - Payments to local shops/vendors
    - Any transaction not automatically tracked
    
    Required: amount, paid_to, purpose, date, payment_method
    """
    try:
        user = current_user["user"]
        user_type = current_user["user_type"]
        
        # Ensure only consumers can use this endpoint
        if user_type != "consumer":
            raise HTTPException(status_code=403, detail="This endpoint is for consumer users only. Use /manual/business instead.")
        
        # Create a Source entry for manual input
        source = Source(
            user_consumer_id=user.id,
            user_business_id=None,
            source_type=TransactionSourceType.MANUAL,
            processed=True,
            processed_at=datetime.utcnow(),
            received_at=datetime.utcnow()
        )
        db.add(source)
        db.flush()
        
        # Get or create merchant
        merchant = db.query(Merchant).filter(
            Merchant.name_normalized.ilike(f"%{transaction_data.paid_to.lower().strip()}%"),
            Merchant.user_consumer_id == user.id
        ).first()
        
        if not merchant:
            merchant = Merchant(
                user_consumer_id=user.id,
                name_normalized=transaction_data.paid_to.lower().strip(),
                name_variants=[transaction_data.paid_to]
            )
            db.add(merchant)
            db.flush()
        
        # Determine payment channel
        payment_channel_map = {
            "cash": PaymentChannel.CASH,
            "card": PaymentChannel.CARD,
            "upi": PaymentChannel.UPI,
            "wallet": PaymentChannel.WALLET
        }
        payment_channel = payment_channel_map.get(
            transaction_data.payment_method.lower(), 
            PaymentChannel.CASH
        )
        
        # Get user categories
        user_categories = settings.DEFAULT_CONSUMER_CATEGORIES
        
        # Use provided category or classify with AI
        category = transaction_data.category
        classification_confidence = 1.0 if category else 0.0
        
        if not category:
            try:
                classification_result = gemini_service.classify_transaction(
                    merchant_name=transaction_data.paid_to,
                    amount=transaction_data.amount,
                    parsed_fields={
                        "purpose": transaction_data.purpose,
                        "payment_method": transaction_data.payment_method
                    },
                    user_categories=user_categories
                )
                category = classification_result["category"]
                classification_confidence = classification_result["confidence"]
            except:
                category = "Unknown"
                classification_confidence = 0.0
        
        # Create transaction
        transaction = Transaction(
            user_consumer_id=user.id,
            user_business_id=None,
            user_type="CONSUMER",
            source_id=source.id,
            merchant_id=merchant.id,
            amount=transaction_data.amount,
            currency="INR",
            date=transaction_data.date,
            merchant_name_raw=transaction_data.paid_to,
            invoice_no=transaction_data.receipt_number,
            payment_channel=payment_channel,
            source_type=TransactionSourceType.MANUAL,
            category=category,
            parsed_fields={
                "purpose": transaction_data.purpose,
                "manual_entry": True,
                "entry_type": "consumer"
            },
            ocr_confidence=1.0,
            classification_confidence=classification_confidence,
            flagged=False,
            confirmed=True
        )
        
        db.add(transaction)
        db.flush()
        
        # Index for RAG
        try:
            rag_service.index_transaction(db, transaction, user.id, user_type)
        except:
            pass
        
        db.commit()
        db.refresh(transaction)
        
        return {
            "success": True,
            "transaction": {
                "id": transaction.id,
                "amount": transaction.amount,
                "paid_to": transaction_data.paid_to,
                "purpose": transaction_data.purpose,
                "category": transaction.category,
                "payment_method": transaction_data.payment_method,
                "date": transaction.date.isoformat()
            },
            "message": "Transaction logged successfully!"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log transaction: {str(e)}")


@router.post("/manual/business")
async def add_business_transaction(
    transaction_data: BusinessManualTransaction,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a manual transaction for BUSINESS users
    
    Perfect for logging:
    - Cash/cheque payments to vendors
    - Income from customers
    - Business expenses
    - Purchases and sales
    - Any business transaction not automatically tracked
    
    Required: amount, party_name, transaction_type, purpose, date, payment_method
    """
    try:
        user = current_user["user"]
        user_type = current_user["user_type"]
        
        # Ensure only businesses can use this endpoint
        if user_type != "business":
            raise HTTPException(status_code=403, detail="This endpoint is for business users only. Use /manual/consumer instead.")
        
        # Create a Source entry for manual input
        source = Source(
            user_consumer_id=None,
            user_business_id=user.id,
            source_type=TransactionSourceType.MANUAL,
            processed=True,
            processed_at=datetime.utcnow(),
            received_at=datetime.utcnow()
        )
        db.add(source)
        db.flush()
        
        # Get or create merchant
        merchant = db.query(Merchant).filter(
            Merchant.name_normalized.ilike(f"%{transaction_data.party_name.lower().strip()}%"),
            Merchant.user_business_id == user.id
        ).first()
        
        if not merchant:
            merchant = Merchant(
                user_business_id=user.id,
                name_normalized=transaction_data.party_name.lower().strip(),
                name_variants=[transaction_data.party_name]
            )
            db.add(merchant)
            db.flush()
        
        # Determine payment channel
        payment_channel_map = {
            "cash": PaymentChannel.CASH,
            "card": PaymentChannel.CARD,
            "upi": PaymentChannel.UPI,
            "cheque": PaymentChannel.BANK_TRANSFER,
            "netbanking": PaymentChannel.NETBANKING,
            "wallet": PaymentChannel.WALLET
        }
        payment_channel = payment_channel_map.get(
            transaction_data.payment_method.lower(), 
            PaymentChannel.CASH
        )
        
        # Get business categories
        user_categories = settings.DEFAULT_BUSINESS_CATEGORIES
        
        # Use provided category or classify with AI
        category = transaction_data.category
        classification_confidence = 1.0 if category else 0.0
        
        if not category:
            try:
                classification_result = gemini_service.classify_transaction(
                    merchant_name=transaction_data.party_name,
                    amount=transaction_data.amount,
                    parsed_fields={
                        "purpose": transaction_data.purpose,
                        "transaction_type": transaction_data.transaction_type,
                        "payment_method": transaction_data.payment_method
                    },
                    user_categories=user_categories
                )
                category = classification_result["category"]
                classification_confidence = classification_result["confidence"]
            except:
                category = "Unknown"
                classification_confidence = 0.0
        
        # Create transaction
        transaction = Transaction(
            user_consumer_id=None,
            user_business_id=user.id,
            user_type="BUSINESS",
            source_id=source.id,
            merchant_id=merchant.id,
            amount=transaction_data.amount,
            currency="INR",
            date=transaction_data.date,
            merchant_name_raw=transaction_data.party_name,
            invoice_no=transaction_data.invoice_number,
            payment_channel=payment_channel,
            source_type=TransactionSourceType.MANUAL,
            category=category,
            parsed_fields={
                "purpose": transaction_data.purpose,
                "transaction_type": transaction_data.transaction_type,
                "gst_amount": transaction_data.gst_amount,
                "payment_terms": transaction_data.payment_terms,
                "reference_number": transaction_data.reference_number,
                "manual_entry": True,
                "entry_type": "business"
            },
            ocr_confidence=1.0,
            classification_confidence=classification_confidence,
            flagged=False,
            confirmed=True
        )
        
        db.add(transaction)
        db.flush()
        
        # Index for RAG
        try:
            rag_service.index_transaction(db, transaction, user.id, user_type)
        except:
            pass
        
        db.commit()
        db.refresh(transaction)
        
        return {
            "success": True,
            "transaction": {
                "id": transaction.id,
                "amount": transaction.amount,
                "party_name": transaction_data.party_name,
                "transaction_type": transaction_data.transaction_type,
                "purpose": transaction_data.purpose,
                "category": transaction.category,
                "payment_method": transaction_data.payment_method,
                "invoice_number": transaction_data.invoice_number,
                "gst_amount": transaction_data.gst_amount,
                "date": transaction.date.isoformat()
            },
            "message": "Business transaction logged successfully!"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log business transaction: {str(e)}")

