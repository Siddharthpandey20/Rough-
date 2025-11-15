"""
n8n Webhook Schemas
Validation schemas for data received from n8n workflows
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


class N8nEmailWebhook(BaseModel):
    """
    Schema for email transaction data from n8n Gmail workflow
    
    Expected payload from n8n after AI parsing:
    {
        "source": "gmail",
        "amount": 1200.50,
        "merchant": "Amazon India",
        "category": "Shopping",
        "date": "2025-11-15T10:30:00Z",
        "payment_method": "UPI",
        "reference_number": "TXN123456789",
        "transaction_type": "debit",
        "email_subject": "Payment Successful",
        "sender_email": "noreply@amazon.in",
        "raw_text": "Full email body..."
    }
    """
    source: str = Field(default="gmail", description="Source identifier (gmail, email)")
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    merchant: str = Field(..., min_length=1, max_length=255, description="Merchant/vendor name")
    category: Optional[str] = Field(None, max_length=100, description="Transaction category")
    date: Optional[datetime] = Field(None, description="Transaction date (ISO format)")
    payment_method: Optional[str] = Field(None, description="Payment method (UPI, CARD, NETBANKING, etc.)")
    reference_number: Optional[str] = Field(None, max_length=255, description="Transaction reference/invoice number")
    transaction_type: Optional[str] = Field("debit", description="Transaction type (debit/credit)")
    
    # Email metadata
    email_subject: Optional[str] = Field(None, max_length=500, description="Email subject line")
    sender_email: Optional[str] = Field(None, max_length=255, description="Sender email address")
    raw_text: Optional[str] = Field(None, description="Raw email body text")
    
    # Additional parsed fields
    currency: str = Field(default="INR", max_length=3, description="Currency code")
    notes: Optional[str] = Field(None, description="Additional notes or description")
    
    @validator('payment_method', pre=True)
    def normalize_payment_method(cls, v):
        """Normalize payment method to uppercase"""
        if v:
            return v.upper()
        return v
    
    @validator('transaction_type', pre=True)
    def normalize_transaction_type(cls, v):
        """Normalize transaction type to lowercase"""
        if v:
            return v.lower()
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "gmail",
                "amount": 1299.00,
                "merchant": "Amazon India",
                "category": "Shopping",
                "date": "2025-11-15T14:30:00Z",
                "payment_method": "UPI",
                "reference_number": "TXN987654321",
                "transaction_type": "debit",
                "email_subject": "Your Amazon.in order has been dispatched",
                "sender_email": "ship-confirm@amazon.in",
                "currency": "INR"
            }
        }


class N8nSMSWebhook(BaseModel):
    """
    Schema for SMS transaction data from SMS-FW.com forwarding service
    
    SMS-FW.com sends in this format:
    Forwarded using https://www.sms-fw.com
    From: 'SENDER_NAME' (+91XXXXXXXXXX)
    To: '#phonenumber-sim1'
    When: 2025-11-15 06:39:55
    ************
    [SMS TEXT HERE]
    
    After parsing, expects:
    {
        "raw_sms": "Full forwarded message",
        "from_name": "ICICIB",
        "from_number": "+919876543210",
        "timestamp": "2025-11-15 06:39:55",
        "sms_body": "Rs 500 debited..."
    }
    """
    # Raw input from SMS-FW.com
    raw_sms: str = Field(..., description="Full forwarded SMS text from SMS-FW.com")
    from_name: Optional[str] = Field(None, description="Sender name from SMS-FW")
    from_number: Optional[str] = Field(None, description="Sender phone number")
    timestamp: Optional[str] = Field(None, description="SMS timestamp from SMS-FW")
    sms_body: Optional[str] = Field(None, description="Extracted SMS body text")
    
    # Parsed transaction fields (populated by endpoint logic)
    amount: Optional[float] = Field(None, gt=0, description="Transaction amount")
    merchant: Optional[str] = Field(None, max_length=255, description="Merchant/payee name")
    upi_id: Optional[str] = Field(None, max_length=255, description="UPI ID/VPA")
    payment_method: Optional[str] = Field(None, description="Payment method")
    reference_number: Optional[str] = Field(None, max_length=255, description="UPI/bank reference")
    transaction_type: Optional[str] = Field(None, description="debit/credit")
    
    # Additional fields
    category: Optional[str] = Field(None, max_length=100, description="Transaction category")
    currency: str = Field(default="INR", max_length=3, description="Currency code")
    account_number: Optional[str] = Field(None, description="Last 4 digits of account")
    balance: Optional[float] = Field(None, description="Account balance after transaction")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @validator('payment_method', pre=True)
    def normalize_payment_method(cls, v):
        """Normalize payment method to uppercase"""
        if v:
            return v.upper()
        return v
    
    @validator('transaction_type', pre=True)
    def normalize_transaction_type(cls, v):
        """Normalize transaction type to lowercase"""
        if v:
            return v.lower()
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "raw_sms": "Forwarded using https://www.sms-fw.com\nFrom: 'ICICIB' (+919876543210)\nTo: '#phonenumber-sim1'\nWhen: 2025-11-15 06:39:55\n************\nRs 299.00 debited from A/c XX1234 to VPA zomato@paytm UPI Ref 434512345678",
                "from_name": "ICICIB",
                "from_number": "+919876543210",
                "timestamp": "2025-11-15 06:39:55",
                "sms_body": "Rs 299.00 debited from A/c XX1234 to VPA zomato@paytm UPI Ref 434512345678"
            }
        }


class N8nWebhookResponse(BaseModel):
    """Standard response for n8n webhook endpoints"""
    success: bool
    transaction_id: Optional[int] = None
    source_id: Optional[int] = None
    message: str
    classification: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "transaction_id": 12345,
                "source_id": 6789,
                "message": "Transaction processed successfully",
                "classification": {
                    "category": "Food & Dining",
                    "confidence": 0.92
                }
            }
        }
