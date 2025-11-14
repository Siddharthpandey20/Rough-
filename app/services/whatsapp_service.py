"""
WhatsApp Integration Service via Twilio
Handles incoming messages and sends notifications
"""

import logging
from typing import Dict, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import settings
from app.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)


class WhatsAppService:
    """WhatsApp integration via Twilio"""
    
    def __init__(self):
        self.client = None
        self.whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER
        
        # Initialize Twilio client if credentials are available
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                self.client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                logger.info("Twilio WhatsApp client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.client = None
        else:
            logger.warning("Twilio credentials not configured")
    
    def is_configured(self) -> bool:
        """Check if WhatsApp service is properly configured"""
        return self.client is not None
    
    def parse_incoming_message(self, message_body: str, from_number: str) -> Optional[Dict]:
        """
        Parse incoming WhatsApp message for transaction data
        
        Args:
            message_body: The text content of the message
            from_number: Sender's WhatsApp number
        
        Returns: Parsed transaction data or None
        """
        try:
            # Check if it's a transaction message
            if not self._is_transaction_message(message_body):
                return None
            
            # Use OCR service's UPI message parser
            parsed_data = ocr_service.parse_upi_message(message_body)
            
            if parsed_data.get('amount'):
                return {
                    'amount': parsed_data['amount'],
                    'merchant': parsed_data.get('upi_id', 'Unknown'),
                    'transaction_type': parsed_data.get('transaction_type', 'unknown'),
                    'payment_method': 'UPI',
                    'reference_number': parsed_data.get('upi_ref'),
                    'date': parsed_data.get('date'),
                    'from_number': from_number,
                    'raw_message': message_body
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Error parsing WhatsApp message: {e}")
            return None
    
    def _is_transaction_message(self, message: str) -> bool:
        """Check if message appears to be a transaction notification"""
        message_lower = message.lower()
        transaction_keywords = [
            'debited', 'credited', 'payment', 'transaction', 'upi',
            'imps', 'neft', 'paid', 'received', 'rs.', 'rs', '₹'
        ]
        return any(keyword in message_lower for keyword in transaction_keywords)
    
    def send_message(self, to_number: str, message: str) -> bool:
        """
        Send WhatsApp message to user
        
        Args:
            to_number: Recipient WhatsApp number (format: whatsapp:+1234567890)
            message: Message content
        
        Returns: True if sent successfully
        """
        try:
            if not self.client:
                logger.error("WhatsApp client not configured")
                return False
            
            # Ensure number has whatsapp: prefix
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            message = self.client.messages.create(
                from_=self.whatsapp_number,
                body=message,
                to=to_number
            )
            
            logger.info(f"WhatsApp message sent: {message.sid}")
            return True
        
        except TwilioRestException as e:
            logger.error(f"Twilio error sending WhatsApp message: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False
    
    def send_anomaly_alert(
        self,
        to_number: str,
        transaction: Dict,
        anomaly_reason: str
    ) -> bool:
        """
        Send anomaly detection alert via WhatsApp
        
        Args:
            to_number: User's WhatsApp number
            transaction: Transaction details
            anomaly_reason: Reason for anomaly flag
        
        Returns: True if sent successfully
        """
        try:
            message = f"""🚨 LUMEN Anomaly Alert

Unusual transaction detected:
💰 Amount: ₹{transaction.get('amount', 0)}
🏪 Merchant: {transaction.get('merchant', 'Unknown')}
📅 Date: {transaction.get('date', 'Unknown')}

⚠️ Reason: {anomaly_reason}

Please review this transaction in the LUMEN app.
Reply 'CONFIRM' to approve or 'REJECT' to flag as suspicious."""
            
            return self.send_message(to_number, message)
        
        except Exception as e:
            logger.error(f"Error sending anomaly alert: {e}")
            return False
    
    def send_transaction_summary(
        self,
        to_number: str,
        summary: Dict
    ) -> bool:
        """
        Send daily/weekly transaction summary
        
        Args:
            to_number: User's WhatsApp number
            summary: Summary data
        
        Returns: True if sent successfully
        """
        try:
            message = f"""📊 LUMEN Transaction Summary

Period: {summary.get('period', 'Today')}
💰 Total Spent: ₹{summary.get('total_spent', 0):.2f}
📝 Transactions: {summary.get('count', 0)}

Top Categories:
"""
            # Add top categories
            top_categories = summary.get('top_categories', [])
            for cat in top_categories[:3]:
                message += f"• {cat['name']}: ₹{cat['amount']:.2f}\n"
            
            message += "\nView details in the LUMEN app."
            
            return self.send_message(to_number, message)
        
        except Exception as e:
            logger.error(f"Error sending transaction summary: {e}")
            return False
    
    def handle_user_reply(self, message_body: str, from_number: str) -> Optional[Dict]:
        """
        Handle user replies to bot messages
        
        Args:
            message_body: User's reply
            from_number: User's WhatsApp number
        
        Returns: Parsed command/reply or None
        """
        try:
            message_lower = message_body.lower().strip()
            
            # Handle greetings
            if any(word in message_lower for word in ['hi', 'hello', 'hey', 'start']):
                return {
                    'action': 'greeting',
                    'from_number': from_number
                }
            
            # Handle confirmation replies
            if message_lower in ['confirm', 'yes', 'ok', 'approve']:
                return {
                    'action': 'confirm_transaction',
                    'from_number': from_number
                }
            
            # Handle rejection replies
            if message_lower in ['reject', 'no', 'suspicious', 'fraud']:
                return {
                    'action': 'reject_transaction',
                    'from_number': from_number
                }
            
            # Handle summary requests
            if any(word in message_lower for word in ['summary', 'report', 'spending']):
                return {
                    'action': 'get_summary',
                    'from_number': from_number
                }
            
            # Handle help requests
            if any(word in message_lower for word in ['help', 'commands']):
                return {
                    'action': 'help',
                    'from_number': from_number
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Error handling user reply: {e}")
            return None
    
    def send_help_message(self, to_number: str) -> bool:
        """Send help message with available commands"""
        try:
            message = """🤖 LUMEN WhatsApp Assistant

I can help you manage your finances! Here's what I can do:

📱 *Automatic Tracking*
Forward your UPI/bank transaction SMS and I'll automatically log them!

💬 *Commands*
• SUMMARY - Get spending overview
• REPORT - View transaction report
• HELP - Show this message

🔔 *Alerts*
I'll notify you about:
• Unusual spending patterns
• Large transactions
• Budget updates

Just forward your transaction messages or ask me for help!"""
            
            return self.send_message(to_number, message)
        
        except Exception as e:
            logger.error(f"Error sending help message: {e}")
            return False


# Global instance
whatsapp_service = WhatsAppService()
