"""
Authentication Schemas
"""

from pydantic import BaseModel, EmailStr
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    user_type: str  # 'consumer' or 'business'


class TokenData(BaseModel):
    user_id: Optional[int] = None
    user_type: Optional[str] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    user_type: str  # 'consumer' or 'business'


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    user_type: str  # 'consumer' or 'business'
    phone: Optional[str] = None
    
    # Optional business fields
    business_name: Optional[str] = None
    contact_person: Optional[str] = None
    gstin: Optional[str] = None
