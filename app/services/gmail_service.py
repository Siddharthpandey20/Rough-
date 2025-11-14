"""
Gmail API Integration Service
Fetches emails and extracts transaction data
"""

import os
import pickle
import logging
import re
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
        Extract transaction data from email content
        
        Returns: Dict with transaction details or None
        """
        try:
            text = f"{subject}\n{body}".lower()
            
            # Check if it's a transaction email
            transaction_keywords = ['payment', 'transaction', 'debited', 'credited', 'upi', 'imps', 'neft', 'purchase', 'receipt']
            if not any(keyword in text for keyword in transaction_keywords):
                return None
            
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
