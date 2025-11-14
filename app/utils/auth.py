"""
Authentication utilities - JWT and password hashing
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import UserConsumer, UserBusiness
from app.schemas.auth import TokenData

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    # Convert user_id to string for JWT 'sub' claim
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        email: str = payload.get("email")
        
        if user_id_str is None or user_type is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Convert string back to int
        user_id = int(user_id_str)
        
        return TokenData(user_id=user_id, user_type=user_type, email=email)
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    # Fetch user based on type
    if token_data.user_type == "consumer":
        user = db.query(UserConsumer).filter(UserConsumer.id == token_data.user_id).first()
    elif token_data.user_type == "business":
        user = db.query(UserBusiness).filter(UserBusiness.id == token_data.user_id).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user type"
        )
    
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Update last active
    user.last_active = datetime.utcnow()
    db.commit()
    
    return {"user": user, "user_type": token_data.user_type}


def authenticate_user(db: Session, email: str, password: str, user_type: str):
    """Authenticate user with email and password"""
    if user_type == "consumer":
        user = db.query(UserConsumer).filter(UserConsumer.email == email).first()
    elif user_type == "business":
        user = db.query(UserBusiness).filter(UserBusiness.email == email).first()
    else:
        return None
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user
