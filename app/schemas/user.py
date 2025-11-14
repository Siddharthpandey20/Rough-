"""
User Schemas
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime


# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None
    timezone: str = "UTC"
    locale: str = "en"
    currency: str = "INR"


# Consumer User Schemas
class UserConsumerCreate(UserBase):
    password: str = Field(..., min_length=8)
    budget_preferences: Optional[Dict] = {}
    personal_category_set: Optional[List[str]] = []


class UserConsumerResponse(UserBase):
    id: int
    budget_preferences: Dict
    personal_category_set: List[str]
    consent_gmail_ingest: bool
    consent_whatsapp_ingest: bool
    consent_upi_ingest: bool
    consent_sms_ingest: bool
    is_active: bool
    created_at: datetime
    last_active: datetime
    
    class Config:
        from_attributes = True


class UserConsumerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    currency: Optional[str] = None
    budget_preferences: Optional[Dict] = None
    personal_category_set: Optional[List[str]] = None


# Business User Schemas
class UserBusinessCreate(UserBase):
    password: str = Field(..., min_length=8)
    business_name: str
    contact_person: str
    gstin: Optional[str] = None
    business_type: Optional[str] = None
    pos_integration: bool = False
    business_category_set: Optional[List[str]] = []
    expected_invoice_rules: Optional[Dict] = {}


class UserBusinessResponse(UserBase):
    id: int
    business_name: str
    contact_person: str
    gstin: Optional[str]
    business_type: Optional[str]
    pos_integration: bool
    business_category_set: List[str]
    expected_invoice_rules: Dict
    consent_gmail_ingest: bool
    consent_whatsapp_ingest: bool
    consent_upi_ingest: bool
    consent_sms_ingest: bool
    is_active: bool
    created_at: datetime
    last_active: datetime
    
    class Config:
        from_attributes = True


class UserBusinessUpdate(BaseModel):
    business_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    business_type: Optional[str] = None
    pos_integration: Optional[bool] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    currency: Optional[str] = None
    business_category_set: Optional[List[str]] = None
    expected_invoice_rules: Optional[Dict] = None


# Consent update schema
class ConsentUpdate(BaseModel):
    consent_gmail_ingest: Optional[bool] = None
    consent_whatsapp_ingest: Optional[bool] = None
    consent_upi_ingest: Optional[bool] = None
    consent_sms_ingest: Optional[bool] = None
