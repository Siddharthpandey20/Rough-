"""
Gmail Background Monitoring Service
Continuously monitors Gmail for transaction emails and processes them automatically
"""

import time
import logging
import os
import pickle
from datetime import datetime, timedelta
from typing import Optional
import threading

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.transaction import Transaction, PaymentChannel, SourceType as TransactionSourceType
from app.models.source import Source
from app.models.merchant import Merchant
from app.services.gemini_service import gemini_service
from app.services.rag_service import rag_service
from app.services.gmail_service import GmailService

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Hardcoded user configuration
MONITORED_USER_EMAIL = "siddharth24102@gmail.com"
MONITORED_USER_ID = 1  # Consumer user ID in database
MONITORED_USER_TYPE = "consumer"


class GmailMonitorService:
    """Background service for continuous Gmail monitoring"""
    
    def __init__(self):
        self.gmail_service = GmailService()
        self.is_running = False
        self.monitor_thread = None
        self.check_interval = 60  # Check every 60 seconds
        self.last_check_time = None
        self.processed_message_ids = set()
        
    def start(self):
        """Start the background monitoring service"""
        if self.is_running:
            logger.warning("Gmail monitor already running")
            return
        
        logger.info(f"🚀 Starting Gmail monitor for {MONITORED_USER_EMAIL}")
        self.is_running = True
        
        # Start monitoring in separate thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("✅ Gmail monitor started successfully")
    
    def stop(self):
        """Stop the background monitoring service"""
        logger.info("Stopping Gmail monitor...")
        self.is_running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("Gmail monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread"""
        # Initial authentication
        try:
            authenticated = self._authenticate()
            if not authenticated:
                logger.error("Failed to authenticate Gmail - monitor stopping")
                self.is_running = False
                return
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.is_running = False
            return
        
        logger.info("Gmail authenticated successfully - starting monitoring loop")
        
        while self.is_running:
            try:
                # Check for new emails
                self._check_new_emails()
                
                # Sleep for check interval
                for _ in range(self.check_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                # Wait before retrying
                time.sleep(30)
    
    def _authenticate(self) -> bool:
        """Authenticate with Gmail using hardcoded user credentials"""
        try:
            creds = None
            token_path = f"{settings.GMAIL_TOKEN_PATH}_{MONITORED_USER_ID}"
            
            # Load existing token
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
                logger.info(f"Loaded existing Gmail token from {token_path}")
            
            # Refresh or create new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired Gmail token...")
                    creds.refresh(Request())
                else:
                    logger.warning("No valid token found - manual authentication required")
                    if not os.path.exists(settings.GMAIL_CREDENTIALS_PATH):
                        logger.error(f"Gmail credentials file not found: {settings.GMAIL_CREDENTIALS_PATH}")
                        return False
                    
                    # This will open browser for OAuth flow
                    logger.info("Starting OAuth flow for Gmail authentication...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.GMAIL_CREDENTIALS_PATH, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info(f"Saved Gmail token to {token_path}")
            
            # Build service
            self.gmail_service.credentials = creds
            self.gmail_service.service = build('gmail', 'v1', credentials=creds)
            
            logger.info(f"✅ Gmail authenticated for {MONITORED_USER_EMAIL}")
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication error: {e}", exc_info=True)
            return False
    
    def _check_new_emails(self):
        """Check for new transaction emails and process them"""
        try:
            if not self.gmail_service.service:
                logger.error("❌ Gmail service not initialized - attempting authentication")
                if not self._authenticate():
                    logger.error("❌ Authentication failed - cannot check emails")
                    return
            
            # Calculate time range
            if self.last_check_time:
                # Check emails since last check
                after_timestamp = int(self.last_check_time.timestamp())
                query = f'after:{after_timestamp} (payment OR transaction OR receipt OR invoice OR UPI OR IMPS OR NEFT OR debited OR credited OR "payment confirmation")'
                logger.info(f"🔍 Checking emails since {self.last_check_time.isoformat()}")
            else:
                # First run - check last 24 hours instead of 1 hour to catch more emails
                after_date = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y/%m/%d')
                query = f'after:{after_date} (payment OR transaction OR receipt OR invoice OR UPI OR IMPS OR NEFT OR debited OR credited OR "payment confirmation")'
                logger.info(f"🔍 First check - searching emails from last 24 hours")
            
            logger.info(f"📧 Gmail query: {query}")
            
            # List messages
            results = self.gmail_service.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()
            
            messages = results.get('messages', [])
            
            if messages:
                logger.info(f"📧 Found {len(messages)} potential transaction emails")
            else:
                logger.info(f"📭 No new transaction emails found")
            
            # Process each message
            new_transactions = 0
            skipped = 0
            for msg in messages:
                msg_id = msg['id']
                
                # Skip if already processed
                if msg_id in self.processed_message_ids:
                    skipped += 1
                    continue
                
                try:
                    logger.info(f"📄 Processing message {msg_id}")
                    success = self._process_email_message(msg_id)
                    if success:
                        new_transactions += 1
                        self.processed_message_ids.add(msg_id)
                        logger.info(f"✅ Message {msg_id} processed successfully")
                    else:
                        logger.info(f"⏭️ Message {msg_id} skipped (not a transaction)")
                        self.processed_message_ids.add(msg_id)  # Mark as processed to avoid checking again
                except Exception as e:
                    logger.error(f"❌ Error processing message {msg_id}: {e}", exc_info=True)
                    continue
            
            if new_transactions > 0:
                logger.info(f"✅ Created {new_transactions} new transaction(s) from Gmail")
            
            if skipped > 0:
                logger.info(f"⏭️ Skipped {skipped} already processed emails")
            
            # Update last check time
            self.last_check_time = datetime.utcnow()
            logger.info(f"✓ Email check completed at {self.last_check_time.isoformat()}")
            
        except HttpError as e:
            logger.error(f"❌ Gmail API error: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"❌ Error checking emails: {e}", exc_info=True)
    
    def _process_email_message(self, message_id: str) -> bool:
        """Process a single email message and create transaction"""
        try:
            # Parse email data
            logger.debug(f"Parsing email message {message_id}")
            transaction_data = self.gmail_service._parse_email_message(message_id)
            
            if not transaction_data:
                logger.debug(f"No transaction data extracted from message {message_id}")
                return False
                
            if not transaction_data.get('amount'):
                logger.debug(f"No amount found in message {message_id}")
                return False
            
            amount = transaction_data['amount']
            merchant = transaction_data.get('merchant', 'Unknown')
            logger.info(f"💰 Processing transaction: {merchant} - ₹{amount}")
            
            # Create transaction in database
            db = SessionLocal()
            try:
                # Create Source record
                source = Source(
                    user_consumer_id=MONITORED_USER_ID,
                    user_business_id=None,
                    source_type=TransactionSourceType.GMAIL,
                    processed=True,
                    processed_at=datetime.utcnow(),
                    received_at=transaction_data.get('email_date', datetime.utcnow())
                )
                db.add(source)
                db.flush()
                logger.debug(f"Created source record ID: {source.id}")
                
                # Get or create merchant
                merchant_name = merchant[:255]
                merchant_obj = db.query(Merchant).filter(
                    Merchant.name_normalized.ilike(f"%{merchant_name.lower().strip()}%"),
                    Merchant.user_consumer_id == MONITORED_USER_ID
                ).first()
                
                if not merchant_obj:
                    merchant_obj = Merchant(
                        user_consumer_id=MONITORED_USER_ID,
                        user_business_id=None,
                        name_normalized=merchant_name.lower().strip(),
                        name_variants=[merchant_name]
                    )
                    db.add(merchant_obj)
                    db.flush()
                    logger.debug(f"Created merchant: {merchant_name}")
                else:
                    logger.debug(f"Using existing merchant: {merchant_name}")
                
                # Determine payment channel
                payment_method = transaction_data.get('payment_method', 'UNKNOWN')
                channel_map = {
                    'UPI': PaymentChannel.UPI,
                    'CARD': PaymentChannel.CARD,
                    'IMPS': PaymentChannel.BANK_TRANSFER,
                    'NEFT': PaymentChannel.BANK_TRANSFER,
                    'NETBANKING': PaymentChannel.NETBANKING
                }
                payment_channel = channel_map.get(payment_method, PaymentChannel.UNKNOWN)
                
                # Classify transaction
                user_categories = settings.DEFAULT_CONSUMER_CATEGORIES
                try:
                    logger.debug(f"Classifying transaction with Gemini AI")
                    classification = gemini_service.classify_transaction(
                        merchant_name=merchant_name,
                        amount=amount,
                        parsed_fields=transaction_data,
                        user_categories=user_categories
                    )
                    category = classification.get('category', 'Unknown')
                    classification_confidence = classification.get('confidence', 0.0)
                    logger.debug(f"Classification: {category} (confidence: {classification_confidence})")
                except Exception as e:
                    logger.error(f"Classification error: {e}")
                    category = 'Unknown'
                    classification_confidence = 0.0
                
                # Create transaction
                transaction = Transaction(
                    user_consumer_id=MONITORED_USER_ID,
                    user_business_id=None,
                    user_type="CONSUMER",
                    source_id=source.id,
                    merchant_id=merchant_obj.id,
                    amount=amount,
                    currency="INR",
                    merchant_name_raw=merchant_name,
                    category=category,
                    date=transaction_data.get('email_date', datetime.utcnow()),
                    payment_channel=payment_channel,
                    source_type=TransactionSourceType.GMAIL,
                    invoice_no=transaction_data.get('reference_number'),
                    confirmed=True,
                    classification_confidence=classification_confidence,
                    ocr_confidence=1.0,
                    parsed_fields={
                        'email_subject': transaction_data.get('subject'),
                        'sender': transaction_data.get('sender'),
                        'transaction_type': transaction_data.get('transaction_type'),
                        'auto_ingested': True
                    }
                )
                db.add(transaction)
                db.flush()
                
                transaction_id = transaction.id
                logger.info(f"💾 Transaction saved to database (ID: {transaction_id})")
                
                # Index for RAG
                try:
                    rag_service.index_transaction(db, transaction, MONITORED_USER_ID, MONITORED_USER_TYPE)
                    logger.debug(f"Transaction {transaction_id} indexed in RAG")
                except Exception as rag_error:
                    logger.error(f"RAG indexing failed: {rag_error}")
                
                db.commit()
                
                logger.info(f"✅ Transaction completed: {merchant_name} - ₹{amount} (ID: {transaction_id})")
                return True
                
            except Exception as db_error:
                logger.error(f"Database error: {db_error}", exc_info=True)
                db.rollback()
                return False
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing email transaction: {e}", exc_info=True)
            return False


# Global instance
gmail_monitor = GmailMonitorService()
