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

# Gmail configuration - shared email that receives SMS forwards
MONITORED_USER_EMAIL = "siddharth24102@iiitnr.edu.in"  # Always check this email
GMAIL_TOKEN_USER_ID = 1  # User ID whose token we use for authentication (token file: gmail_token.json_1)


class GmailMonitorService:
    """Background service for continuous Gmail monitoring"""
    
    def __init__(self):
        self.gmail_service = GmailService()
        self.is_running = False
        self.monitor_thread = None
        self.check_interval = 30  # Check every 30 seconds for faster detection
        self.last_check_time = None
        self.processed_message_ids = set()
        # User who will receive the transactions - CRITICAL for correct database storage
        self.current_user_id = None
        self.current_user_type = None
        
    def start(self, user_id: int, user_type: str):
        """Start the background monitoring service
        
        Args:
            user_id: The user ID to save transactions to (REQUIRED)
            user_type: Either "consumer" or "business" (REQUIRED)
        """
        if self.is_running:
            logger.warning("Gmail monitor already running")
            return
        
        # CRITICAL: Set the user who will receive ALL transactions
        self.current_user_id = user_id
        self.current_user_type = user_type
        
        logger.info(f"🚀 Starting Gmail monitor")
        logger.info(f"📧 Monitoring email: {MONITORED_USER_EMAIL}")
        logger.info(f"💾 ALL TRANSACTIONS WILL BE SAVED TO: User ID {self.current_user_id} ({self.current_user_type})")
        logger.info(f"🔍 Any transaction found in {MONITORED_USER_EMAIL} will go to User {self.current_user_id}")
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
            token_path = f"{settings.GMAIL_TOKEN_PATH}_{GMAIL_TOKEN_USER_ID}"
            
            # Load existing token
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
                logger.info(f"📂 Loaded existing Gmail token from {token_path}")
            
            # Refresh or create new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("🔄 Refreshing expired Gmail token...")
                    try:
                        creds.refresh(Request())
                        logger.info("✅ Token refreshed successfully")
                    except Exception as refresh_error:
                        logger.error(f"❌ Token refresh failed: {refresh_error}")
                        # Delete invalid token and require re-authentication
                        if os.path.exists(token_path):
                            os.remove(token_path)
                        logger.warning("🔐 Please re-authenticate by calling /api/v1/n8n/gmail/authenticate")
                        return False
                else:
                    logger.warning("⚠️ No valid token found - manual authentication required")
                    if not os.path.exists(settings.GMAIL_CREDENTIALS_PATH):
                        logger.error(f"❌ Gmail credentials file not found: {settings.GMAIL_CREDENTIALS_PATH}")
                        logger.error("📝 Please ensure gmail_credentials.json exists in credentials/ folder")
                        return False
                    
                    # This will open browser for OAuth flow
                    logger.info("🔐 Starting OAuth flow for Gmail authentication...")
                    logger.info("🌐 A browser window will open - please authorize the application")
                    logger.info(f"📧 Authenticating as: {MONITORED_USER_EMAIL}")
                    logger.info("⚠️ If you get redirect_uri_mismatch error, run: python test_gmail_auth.py")
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            settings.GMAIL_CREDENTIALS_PATH, SCOPES
                        )
                        
                        # Try multiple ports
                        ports_to_try = [8080, 8090, 0]
                        auth_success = False
                        
                        for port in ports_to_try:
                            try:
                                logger.info(f"🔄 Attempting OAuth on port {port if port != 0 else 'auto'}...")
                                creds = flow.run_local_server(
                                    port=port,
                                    success_message='✅ Authentication successful! You can close this window.',
                                    open_browser=True
                                )
                                auth_success = True
                                logger.info("✅ OAuth flow completed successfully")
                                break
                            except Exception as port_error:
                                if 'redirect_uri_mismatch' in str(port_error).lower():
                                    logger.warning(f"❌ Port {port} failed: redirect_uri_mismatch")
                                    continue
                                else:
                                    raise port_error
                        
                        if not auth_success:
                            raise Exception("All OAuth port attempts failed")
                            
                    except Exception as oauth_error:
                        logger.error(f"❌ OAuth flow failed: {oauth_error}")
                        logger.error("💡 Try calling POST /api/v1/n8n/gmail/authenticate endpoint manually")
                        logger.error("💡 Or run: python test_gmail_auth.py")
                        return False
                
                # Save credentials
                try:
                    with open(token_path, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info(f"💾 Saved Gmail token to {token_path}")
                except Exception as save_error:
                    logger.error(f"❌ Failed to save token: {save_error}")
            
            # Build service
            self.gmail_service.credentials = creds
            self.gmail_service.service = build('gmail', 'v1', credentials=creds)
            # Verify authenticated account matches the monitored email
            try:
                profile = self.gmail_service.service.users().getProfile(userId='me').execute()
                authenticated_email = profile.get('emailAddress')
                logger.info(f"📧 Authenticated Gmail account: {authenticated_email}")
                if authenticated_email and authenticated_email.lower() != MONITORED_USER_EMAIL.lower():
                    logger.error(
                        f"🔐 Authenticated account mismatch: expected {MONITORED_USER_EMAIL}, got {authenticated_email}"
                    )
                    # Remove the token so user can re-authenticate cleanly
                    try:
                        if os.path.exists(token_path):
                            os.remove(token_path)
                            logger.info(f"🗑️ Removed token at {token_path} due to account mismatch")
                    except Exception as rm_err:
                        logger.warning(f"Could not remove token file: {rm_err}")

                    logger.warning("Please re-authenticate with the correct account:")
                    logger.warning("  1) Call POST /api/v1/n8n/gmail/authenticate or run test_gmail_auth.py")
                    logger.warning("  2) When browser opens, sign in with the monitored Gmail account")
                    return False

            except Exception:
                logger.debug("Could not verify authenticated profile email; proceeding anyway")

            logger.info(f"✅ Gmail authenticated successfully for {MONITORED_USER_EMAIL}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Gmail authentication error: {e}", exc_info=True)
            logger.error("💡 To authenticate manually: POST /api/v1/n8n/gmail/authenticate")
            return False
    
    def _check_new_emails(self):
        """Check for new UNREAD transaction emails and process them"""
        try:
            if not self.gmail_service.service:
                logger.error("❌ Gmail service not initialized - attempting authentication")
                if not self._authenticate():
                    logger.error("❌ Authentication failed - cannot check emails")
                    return
            
            # Calculate time range and build query with is:unread filter
            if self.last_check_time:
                # Check emails since last check
                after_timestamp = int(self.last_check_time.timestamp())
                query = f'is:unread after:{after_timestamp} (payment OR transaction OR receipt OR invoice OR UPI OR IMPS OR NEFT OR debited OR credited OR "payment confirmation" OR bank OR "Rs." OR "INR" OR "₹")'
                logger.info(f"🔍 Checking UNREAD emails since {self.last_check_time.isoformat()}")
            else:
                # First run - check last 7 days to catch any pending emails
                after_date = (datetime.utcnow() - timedelta(days=7)).strftime('%Y/%m/%d')
                query = f'is:unread after:{after_date} (payment OR transaction OR receipt OR invoice OR UPI OR IMPS OR NEFT OR debited OR credited OR "payment confirmation" OR bank OR "Rs." OR "INR" OR "₹")'
                logger.info(f"🔍 First check - searching UNREAD emails from last 7 days")
            
            logger.debug(f"📧 Gmail query: {query}")
            
            # List messages
            results = self.gmail_service.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()
            
            messages = results.get('messages', [])
            
            if messages:
                logger.info(f"📧 Found {len(messages)} UNREAD potential transaction emails")
            else:
                logger.debug(f"📭 No new unread transaction emails found")
            
            # Process each message
            new_transactions = 0
            failed = 0
            
            for msg in messages:
                msg_id = msg['id']
                
                # Skip if already processed successfully
                if msg_id in self.processed_message_ids:
                    continue
                
                try:
                    logger.info(f"📄 Processing message {msg_id}")
                    success = self._process_email_message(msg_id)
                    if success:
                        new_transactions += 1
                        self.processed_message_ids.add(msg_id)
                        # Mark email as read after successful processing
                        try:
                            self.gmail_service.service.users().messages().modify(
                                userId='me',
                                id=msg_id,
                                body={'removeLabelIds': ['UNREAD']}
                            ).execute()
                            logger.debug(f"✓ Marked email {msg_id} as read")
                        except Exception as mark_error:
                            logger.warning(f"Could not mark email as read: {mark_error}")
                        
                        logger.info(f"✅ Message {msg_id} processed successfully - transaction created")
                    else:
                        # DON'T mark as processed - let it be retried next time
                        # Only the successful creation of transaction marks email as processed
                        logger.warning(f"⚠️  Message {msg_id} failed to create transaction - will retry next check")
                        logger.warning(f"   This usually means Gemini AI couldn't extract transaction data")
                        failed += 1
                except Exception as e:
                    logger.error(f"❌ Error processing message {msg_id}: {e}", exc_info=True)
                    # DON'T mark as processed on exception - retry next time
                    logger.error(f"   Will retry this message on next check")
                    failed += 1
                    continue
            
            # Summary logging
            if new_transactions > 0:
                logger.info(f"✅ Created {new_transactions} new transaction(s) from Gmail")
            
            if failed > 0:
                logger.warning(f"❌ {failed} emails failed to create transactions (will retry next check)")
            
            if new_transactions == 0 and failed == 0 and len(messages) == 0:
                logger.debug(f"✓ No new unread transaction emails at {datetime.utcnow().isoformat()}")
            
            # Update last check time
            self.last_check_time = datetime.utcnow()
            
        except HttpError as e:
            logger.error(f"❌ Gmail API error: {e}", exc_info=True)
            if 'invalid_grant' in str(e) or '401' in str(e):
                logger.error("🔐 Token expired or invalid - please re-authenticate")
                logger.error("💡 Call POST /api/v1/n8n/gmail/authenticate to re-authenticate")
        except Exception as e:
            logger.error(f"❌ Error checking emails: {e}", exc_info=True)
    
    def _process_email_message(self, message_id: str) -> bool:
        """Process a single email message and create transaction"""
        try:
            # CRITICAL: Check that we have a user to save transactions to
            if not self.current_user_id:
                logger.error("❌ No user ID configured for transactions! Monitor started incorrectly.")
                logger.error("💡 Call /api/v1/n8n/gmail/start with authentication to set user ID")
                return False
            
            # Parse email data
            logger.info(f"📧 Parsing email message {message_id}")
            transaction_data = self.gmail_service._parse_email_message(message_id)
            
            logger.info(f"📊 Extracted transaction_data: {transaction_data}")
            
            if not transaction_data:
                logger.warning(f"❌ No transaction data extracted from message {message_id}")
                return False
                
            if not transaction_data.get('amount'):
                logger.warning(f"❌ No amount found in message {message_id}. Data: {transaction_data}")
                return False
            
            amount = transaction_data['amount']
            merchant = transaction_data.get('merchant') or 'Unknown'
            gemini_confidence = transaction_data.get('gemini_confidence', 'N/A')
            logger.info(f"💰 Processing transaction: {merchant} - ₹{amount} (Gemini confidence: {gemini_confidence})")
            logger.info(f"💾 Transaction will be saved to User ID: {self.current_user_id} ({self.current_user_type})")
            
            # Create transaction in database
            db = SessionLocal()
            try:
                # Create Source record for THIS USER
                source = Source(
                    user_consumer_id=self.current_user_id if self.current_user_type == 'consumer' else None,
                    user_business_id=self.current_user_id if self.current_user_type == 'business' else None,
                    source_type=TransactionSourceType.GMAIL,
                    processed=True,
                    processed_at=datetime.utcnow(),
                    received_at=transaction_data.get('email_date', datetime.utcnow())
                )
                db.add(source)
                db.flush()
                logger.debug(f"Created source record ID: {source.id} for user {self.current_user_id}")
                
                # Get or create merchant FOR THIS USER
                merchant_name = str(merchant)[:255] if merchant else 'Unknown'
                if self.current_user_type == 'consumer':
                    merchant_obj = db.query(Merchant).filter(
                        Merchant.name_normalized.ilike(f"%{merchant_name.lower().strip()}%"),
                        Merchant.user_consumer_id == self.current_user_id
                    ).first()
                else:
                    merchant_obj = db.query(Merchant).filter(
                        Merchant.name_normalized.ilike(f"%{merchant_name.lower().strip()}%"),
                        Merchant.user_business_id == self.current_user_id
                    ).first()
                
                if not merchant_obj:
                    merchant_obj = Merchant(
                        user_consumer_id=self.current_user_id if self.current_user_type == 'consumer' else None,
                        user_business_id=self.current_user_id if self.current_user_type == 'business' else None,
                        name_normalized=merchant_name.lower().strip(),
                        name_variants=[merchant_name]
                    )
                    db.add(merchant_obj)
                    db.flush()
                    logger.debug(f"Created merchant: {merchant_name} for user {self.current_user_id}")
                else:
                    logger.debug(f"Using existing merchant: {merchant_name} for user {self.current_user_id}")
                
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
                if self.current_user_type == 'consumer':
                    user_categories = settings.DEFAULT_CONSUMER_CATEGORIES
                else:
                    user_categories = settings.DEFAULT_BUSINESS_CATEGORIES
                    
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
                
                # Create transaction FOR THIS USER
                transaction = Transaction(
                    user_consumer_id=self.current_user_id if self.current_user_type == 'consumer' else None,
                    user_business_id=self.current_user_id if self.current_user_type == 'business' else None,
                    user_type="CONSUMER" if self.current_user_type == 'consumer' else "BUSINESS",
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
                        'auto_ingested': True,
                        'monitored_email': MONITORED_USER_EMAIL
                    }
                )
                db.add(transaction)
                db.flush()
                
                transaction_id = transaction.id
                logger.info(f"💾 Transaction created in session (ID: {transaction_id}) for user {self.current_user_id}")
                
                # Index for RAG
                try:
                    rag_service.index_transaction(db, transaction, self.current_user_id, self.current_user_type)
                    logger.debug(f"Transaction {transaction_id} indexed in RAG for user {self.current_user_id}")
                except Exception as rag_error:
                    logger.error(f"RAG indexing failed: {rag_error}")
                
                logger.info(f"💾 Committing transaction to database...")
                db.commit()
                logger.info(f"✅ Transaction committed successfully (ID: {transaction_id})")
                
                logger.info(f"✅ Transaction completed: {merchant_name} - ₹{amount} (ID: {transaction_id}) -> User {self.current_user_id}")
                return True
                
            except Exception as db_error:
                logger.error(f"❌ Database error: {db_error}", exc_info=True)
                logger.error(f"❌ Transaction data that failed: amount={amount}, merchant={merchant}, user_id={self.current_user_id}")
                db.rollback()
                logger.info(f"🔄 Database rolled back")
                return False
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing email transaction: {e}", exc_info=True)
            return False


# Global instance
gmail_monitor = GmailMonitorService()
