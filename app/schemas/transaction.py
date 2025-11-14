"""
Transaction Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class TransactionBase(BaseModel):
    amount: float
    currency: str = "INR"
    date: datetime
    merchant_name_raw: Optional[str] = None
    invoice_no: Optional[str] = None
    payment_channel: str
    source_type: str
    category: Optional[str] = None


class TransactionCreate(TransactionBase):
    user_type: str
    source_id: int
    merchant_id: Optional[int] = None
    parsed_fields: Optional[Dict] = {}
    ocr_confidence: Optional[float] = 0.0


class TransactionResponse(TransactionBase):
    id: int
    user_type: str
    source_id: int
    merchant_id: Optional[int]
    ocr_confidence: float
    classification_confidence: float
    flagged: bool
    anomaly_score: Optional[float]
    anomaly_reason: Optional[str]
    confirmed: Optional[bool]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TransactionUpdate(BaseModel):
    category: Optional[str] = None
    confirmed: Optional[bool] = None
    merchant_id: Optional[int] = None


class TransactionConfirmation(BaseModel):
    transaction_id: int
    confirmed: bool  # True = confirm, False = reject
    corrected_category: Optional[str] = None
    notes: Optional[str] = None


class TransactionQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category: Optional[str] = None
    merchant_id: Optional[int] = None
    flagged_only: bool = False
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    source_type: Optional[str] = None
    payment_channel: Optional[str] = None
    limit: int = Field(default=100, le=1000)
    offset: int = 0


class TransactionStats(BaseModel):
    total_transactions: int
    total_amount: float
    avg_amount: float
    flagged_count: int
    by_category: Dict[str, float]
    by_payment_channel: Dict[str, int]
    by_source_type: Dict[str, int]


class ConsumerManualTransaction(BaseModel):
    """Schema for consumers to manually log personal transactions (cash, etc.)"""
    amount: float = Field(..., description="Amount paid", example=500.00)
    paid_to: str = Field(..., description="Who you paid (person/business name)", example="Local Grocery Store")
    purpose: str = Field(..., description="Why you paid (reason/description)", example="Weekly grocery shopping")
    date: datetime = Field(..., description="When did you pay", example="2025-11-14T10:30:00")
    payment_method: str = Field(..., description="How did you pay: cash/card/upi/wallet", example="cash")
    category: Optional[str] = Field(None, description="Optional: Groceries, Food, Transport, etc.")
    receipt_number: Optional[str] = Field(None, description="Optional: Receipt/bill number if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 250.00,
                "paid_to": "Uber Driver",
                "purpose": "Cab ride to office",
                "date": "2025-11-14T09:00:00",
                "payment_method": "cash",
                "category": "Transport",
                "receipt_number": None
            }
        }


class BusinessManualTransaction(BaseModel):
    """Schema for businesses to manually log business transactions"""
    amount: float = Field(..., description="Transaction amount", example=15000.00)
    party_name: str = Field(..., description="Vendor/Customer/Supplier name", example="ABC Suppliers Pvt Ltd")
    transaction_type: str = Field(..., description="expense/income/purchase/sale", example="expense")
    purpose: str = Field(..., description="Purpose/description of transaction", example="Office furniture purchase")
    date: datetime = Field(..., description="Transaction date", example="2025-11-14T14:00:00")
    payment_method: str = Field(..., description="cash/card/upi/cheque/netbanking/wallet", example="cheque")
    category: Optional[str] = Field(None, description="Inventory, Salary, Services, etc.")
    invoice_number: Optional[str] = Field(None, description="Invoice/Bill number")
    gst_amount: Optional[float] = Field(None, description="GST/Tax amount if applicable")
    payment_terms: Optional[str] = Field(None, description="e.g., 'Paid in full', 'Credit 30 days'")
    reference_number: Optional[str] = Field(None, description="Cheque number, transaction reference, etc.")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 50000.00,
                "party_name": "XYZ Vendors Ltd",
                "transaction_type": "expense",
                "purpose": "Raw material purchase for production",
                "date": "2025-11-14T11:00:00",
                "payment_method": "cheque",
                "category": "Inventory",
                "invoice_number": "INV-2024-001",
                "gst_amount": 9000.00,
                "payment_terms": "Paid in full",
                "reference_number": "CHQ-123456"
            }
        }

