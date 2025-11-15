"""
Gmail API Integration Service
Fetches emails and extracts transaction data
"""

import os
import pickle
import logging
import re
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailService:
    """Gmail API integration service"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
    
    def authenticate(self, user_id: int) -> bool:
        """
        Authenticate with Gmail API
        
        Returns: True if authentication successful
        """
        try:
            creds = None
            token_path = f"{settings.GMAIL_TOKEN_PATH}_{user_id}"
            
            # Load existing token
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # Refresh or create new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(settings.GMAIL_CREDENTIALS_PATH):
                        logger.error(f"Gmail credentials file not found: {settings.GMAIL_CREDENTIALS_PATH}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.GMAIL_CREDENTIALS_PATH, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.credentials = creds
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info(f"Gmail authenticated successfully for user {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Gmail authentication error: {e}")
            return False
    
    def get_oauth_url(self) -> str:
        """
        Get OAuth authorization URL
        
        Returns: Authorization URL for user to visit
        """
        try:
            if not os.path.exists(settings.GMAIL_CREDENTIALS_PATH):
                raise FileNotFoundError(f"Gmail credentials file not found: {settings.GMAIL_CREDENTIALS_PATH}")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.GMAIL_CREDENTIALS_PATH, SCOPES
            )
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            return auth_url
        
        except Exception as e:
            logger.error(f"Failed to generate OAuth URL: {e}")
            return ""
    
    def fetch_transaction_emails(
        self,
        days_back: int = 30,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Fetch transaction-related emails from Gmail
        
        Returns: List of parsed transaction emails
        """
        try:
            if not self.service:
                logger.error("Gmail service not authenticated")
                return []
            
            # Calculate date range
            after_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            
            # Search query for transaction emails
            query = f'after:{after_date} (payment OR transaction OR receipt OR invoice OR UPI OR IMPS OR NEFT OR debited OR credited OR "payment confirmation")'
            
            # List messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} potential transaction emails")
            
            # Parse each message
            transactions = []
            for msg in messages:
                try:
                    transaction = self._parse_email_message(msg['id'])
                    if transaction:
                        transactions.append(transaction)
                except Exception as e:
                    logger.error(f"Error parsing message {msg['id']}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(transactions)} transaction emails")
            return transactions
        
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def _parse_email_message(self, message_id: str) -> Optional[Dict]:
        """
        Parse a single email message to extract transaction data
        
        Returns: Transaction data dict or None
        """
        try:
            # Get full message
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            subject = headers.get('Subject', '')
            sender = headers.get('From', '')
            date_str = headers.get('Date', '')
            
            # Parse date
            try:
                email_date = parsedate_to_datetime(date_str)
            except:
                email_date = datetime.utcnow()
            
            # Extract body
            body = self._get_email_body(message['payload'])
            
            # Parse transaction data
            transaction_data = self._extract_transaction_data(subject, body, sender)
            
            if transaction_data:
                transaction_data.update({
                    'email_id': message_id,
                    'email_date': email_date,
                    'sender': sender,
                    'subject': subject
                })
                return transaction_data
            
            return None
        
        except Exception as e:
            logger.error(f"Error parsing email message: {e}")
            return None
    
    def _get_email_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        try:
            body = ""
            
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    elif part['mimeType'] == 'text/html':
                        data = part['body'].get('data', '')
                        html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        # Extract text from HTML
                        soup = BeautifulSoup(html, 'html.parser')
                        body += soup.get_text()
            else:
                data = payload['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            return body
        
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return ""
    
    def _extract_transaction_data(self, subject: str, body: str, sender: str) -> Optional[Dict]:
        """
        Extract transaction data from email content using Gemini AI
        
        Returns: Dict with transaction details or None
        """
        try:
            text = f"{subject}\n{body}"
            text_lower = text.lower()
            
            # Quick keyword check to filter non-transaction emails
            transaction_keywords = ['payment', 'transaction', 'debited', 'credited', 'upi', 'imps', 'neft', 'purchase', 'receipt', 'rs.', 'inr', '₹', 'bank', 'transfer', 'paid', 'amount']
            if not any(keyword in text_lower for keyword in transaction_keywords):
                logger.debug(f"Email does not contain transaction keywords - skipping")
                return None
            
            # Use Gemini AI to extract transaction data
            logger.info(f"🤖 Using Gemini AI to extract transaction data from email")
            logger.info(f"📧 Subject: {subject[:100]}")
            logger.info(f"📤 Sender: {sender}")
            
            prompt = f"""You are a financial transaction parser. Analyze this email and extract transaction details.

Email Subject: {subject}
Email Sender: {sender}
Email Body:
{body[:2000]}  # Limit to first 2000 chars

Task: Determine if this is a payment/transaction email and extract structured data.

Respond ONLY with valid JSON in this exact format:
{{
    "is_transaction": true/false,
    "amount": 299.00,
    "merchant": "merchant_name",
    "transaction_type": "debit" or "credit",
    "payment_method": "UPI" or "CARD" or "IMPS" or "NEFT" or "NETBANKING" or "UNKNOWN",
    "reference_number": "ref_number_if_available",
    "confidence": 0.95
}}

Rules:
1. is_transaction must be true only if this is a real payment/transaction notification
2. Extract amount as a number (e.g., 299.00, not "Rs 299")
3. merchant should be the payee/merchant name
4. transaction_type: "debit" if money was deducted, "credit" if received
5. If you cannot extract with >60% confidence, set is_transaction to false
6. Set confidence score (0-1) based on how clear the transaction details are

Examples of transaction emails:
- "Rs 299 debited from A/c XX1234 to VPA zomato@paytm"
- "Payment of INR 500 successful at Amazon"
- "You have received ₹750 from john@upi"

Examples of NON-transaction emails:
- Marketing emails
- Promotional offers
- Account statements
- Newsletters"""

            try:
                response = gemini_service._call_with_retry(
                    gemini_service.model.generate_content,
                    prompt
                )
                result_text = response.text.strip()
                
                # Extract JSON from response
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                result = json.loads(result_text)
                
                logger.info(f"🤖 Gemini response: is_transaction={result.get('is_transaction')}, confidence={result.get('confidence')}")
                
                # Check if it's a transaction email
                if not result.get('is_transaction', False):
                    logger.info(f"⏭️ Gemini determined email is not a transaction (confidence: {result.get('confidence', 0)})")
                    return None
                
                # Validate required fields
                if not result.get('amount') or result.get('amount') <= 0:
                    logger.warning(f"❌ Invalid or missing amount in extracted data: {result.get('amount')}")
                    return None
                
                # Check confidence threshold
                if result.get('confidence', 0) < 0.6:
                    logger.info(f"⏭️ Low confidence ({result.get('confidence', 0)}) - skipping")
                    return None
                
                transaction_data = {
                    'amount': float(result.get('amount', 0)),
                    'merchant': result.get('merchant', 'Unknown')[:100],
                    'transaction_type': result.get('transaction_type', 'debit'),
                    'payment_method': result.get('payment_method', 'UNKNOWN'),
                    'reference_number': result.get('reference_number'),
                    'gemini_confidence': result.get('confidence', 0)
                }
                
                logger.info(f"✅ Gemini extracted: {transaction_data['merchant']} - ₹{transaction_data['amount']} (confidence: {transaction_data['gemini_confidence']})")
                logger.info(f"📦 Full transaction_data: {transaction_data}")
                return transaction_data
                
            except json.JSONDecodeError as je:
                logger.error(f"❌ Failed to parse Gemini JSON response: {je}")
                logger.error(f"📄 Gemini response was: {result_text[:200]}")
                # Fall back to regex extraction
                logger.info(f"🔄 Falling back to regex extraction...")
                return self._fallback_regex_extraction(text, sender)
            
            except Exception as gemini_error:
                logger.error(f"Gemini extraction failed: {gemini_error}")
                # Fall back to regex extraction
                return self._fallback_regex_extraction(text, sender)
        
        except Exception as e:
            logger.error(f"Error extracting transaction data: {e}")
            return None
    
    def _fallback_regex_extraction(self, text: str, sender: str) -> Optional[Dict]:
        """Fallback regex-based extraction if Gemini fails"""
        try:
            text_lower = text.lower()
            transaction_data = {
                'amount': None,
                'merchant': None,
                'date': None,
                'transaction_type': None,
                'payment_method': None,
                'reference_number': None
            }
            
            # Extract amount
            amount_patterns = [
                r'(?:rs\.?|inr|₹)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'amount[:\s]*(?:rs\.?|inr|₹)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'(?:debited|credited|paid)[:\s]*(?:rs\.?|inr|₹)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            ]
            
            for pattern in amount_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        transaction_data['amount'] = float(amount_str)
                        break
                    except:
                        continue
            
            # Determine transaction type
            if 'debited' in text_lower or 'debit' in text_lower or 'paid' in text_lower:
                transaction_data['transaction_type'] = 'debit'
            elif 'credited' in text_lower or 'credit' in text_lower or 'received' in text_lower:
                transaction_data['transaction_type'] = 'credit'
            
            # Extract merchant/payee
            merchant_patterns = [
                r'(?:to|at|from)\s+(?:vpa\s+)?([a-z0-9._-]+@[a-z]+)',  # UPI ID like zomato@paytm
                r'(?:to|at|from)\s+([A-Za-z0-9\s&\.-]+?)(?:\s+on|\s+for|\s+via|\s+upi|\.|\n)',
                r'merchant[:\s]+([A-Za-z0-9\s&\.-]+?)(?:\s+on|\.|\n)',
                r'payee[:\s]+([A-Za-z0-9\s&\.-]+?)(?:\s+on|\.|\n)',
                r'paid to\s+([A-Za-z0-9\s&\.-]+?)(?:\s+on|\.|\n)',
            ]
            
            for pattern in merchant_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    merchant = match.group(1).strip()
                    if len(merchant) > 2:
                        # If it's a UPI ID, extract the merchant name before @
                        if '@' in merchant:
                            merchant = merchant.split('@')[0]
                        transaction_data['merchant'] = merchant[:100]
                        break
            
            # If still no merchant, try to extract from sender if it's from a bank
            if not transaction_data['merchant']:
                if any(bank in sender.lower() for bank in ['bank', 'icici', 'hdfc', 'sbi', 'axis', 'kotak']):
                    transaction_data['merchant'] = 'Bank Transaction'
                else:
                    transaction_data['merchant'] = 'Unknown'
            
            # Extract payment method
            if 'upi' in text_lower:
                transaction_data['payment_method'] = 'UPI'
            elif 'card' in text_lower or 'credit card' in text_lower or 'debit card' in text_lower:
                transaction_data['payment_method'] = 'CARD'
            elif 'imps' in text_lower:
                transaction_data['payment_method'] = 'IMPS'
            elif 'neft' in text_lower:
                transaction_data['payment_method'] = 'NEFT'
            elif 'netbanking' in text_lower:
                transaction_data['payment_method'] = 'NETBANKING'
            
            # Extract reference number
            ref_patterns = [
                r'(?:ref|reference|transaction id|txn)[:\s#]*([A-Z0-9]{10,})',
                r'upi\s+ref[:\s]*([A-Z0-9]{10,})'
            ]
            
            for pattern in ref_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    transaction_data['reference_number'] = match.group(1)
                    break
            
            # Return only if we have minimum required data
            if transaction_data['amount']:
                logger.debug(f"Fallback regex extracted: {transaction_data['merchant']} - ₹{transaction_data['amount']}")
                return transaction_data
            
            return None
        
        except Exception as e:
            logger.error(f"Fallback extraction error: {e}")
            return None
            
            for pattern in amount_patterns:
                match = re.search(pattern, text)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        transaction_data['amount'] = float(amount_str)
                        break
                    except:
                        continue
            
            # Determine transaction type
            if 'debited' in text or 'debit' in text or 'paid' in text:
                transaction_data['transaction_type'] = 'debit'
            elif 'credited' in text or 'credit' in text or 'received' in text:
                transaction_data['transaction_type'] = 'credit'
            
            # Extract merchant/payee
            merchant_patterns = [
                r'(?:to|at|from)\s+([A-Za-z0-9\s&\.-]+?)(?:\s+on|\s+for|\s+via|\.|\n)',
                r'merchant[:\s]+([A-Za-z0-9\s&\.-]+?)(?:\s+on|\.|\n)',
                r'payee[:\s]+([A-Za-z0-9\s&\.-]+?)(?:\s+on|\.|\n)'
            ]
            
            for pattern in merchant_patterns:
                match = re.search(pattern, text)
                if match:
                    merchant = match.group(1).strip()
                    if len(merchant) > 3:
                        transaction_data['merchant'] = merchant[:100]
                        break
            
            # Extract payment method
            if 'upi' in text:
                transaction_data['payment_method'] = 'UPI'
            elif 'card' in text or 'credit card' in text or 'debit card' in text:
                transaction_data['payment_method'] = 'CARD'
            elif 'imps' in text:
                transaction_data['payment_method'] = 'IMPS'
            elif 'neft' in text:
                transaction_data['payment_method'] = 'NEFT'
            elif 'netbanking' in text:
                transaction_data['payment_method'] = 'NETBANKING'
            
            # Extract reference number
            ref_patterns = [
                r'(?:ref|reference|transaction id|txn)[:\s#]*([A-Z0-9]{10,})',
                r'upi\s+ref[:\s]*([A-Z0-9]{10,})'
            ]
            
            for pattern in ref_patterns:
                match = re.search(pattern, text)
                if match:
                    transaction_data['reference_number'] = match.group(1)
                    break
            
            # Return only if we have minimum required data
            if transaction_data['amount']:
                return transaction_data
            
            return None
        
        except Exception as e:
            logger.error(f"Error extracting transaction data: {e}")
            return None
    
    def is_authenticated(self, user_id: int) -> bool:
        """Check if user has authenticated Gmail"""
        token_path = f"{settings.GMAIL_TOKEN_PATH}_{user_id}"
        return os.path.exists(token_path)


# Global instance
gmail_service = GmailService()
