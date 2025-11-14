"""
Authentication Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.core.database import get_db, get_audit_db
from app.core.config import settings
from app.schemas.auth import LoginRequest, RegisterRequest, Token
from app.schemas.user import UserConsumerResponse, UserBusinessResponse
from app.models.user import UserConsumer, UserBusiness
from app.utils.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_user
)
from app.utils.audit import AuditLogger
from app.models.audit import AuditActor, AuditAction

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
    audit_db: Session = Depends(get_audit_db)
):
    """
    Register a new user (Consumer or Business)
    
    **Request Body:**
    - email: Valid email address
    - password: Minimum 8 characters
    - name: User's name
    - user_type: "consumer" or "business"
    - phone: Optional phone number
    - business_name: Required if user_type is "business"
    - contact_person: Required if user_type is "business"
    """
    try:
        # Check if user already exists
        if request.user_type == "consumer":
            existing = db.query(UserConsumer).filter(UserConsumer.email == request.email).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create consumer user
            hashed_password = get_password_hash(request.password)
            user = UserConsumer(
                email=request.email,
                name=request.name,
                phone=request.phone,
                hashed_password=hashed_password,
                personal_category_set=settings.DEFAULT_CONSUMER_CATEGORIES
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            user_id = user.id
        
        elif request.user_type == "business":
            existing = db.query(UserBusiness).filter(UserBusiness.email == request.email).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            if not request.business_name or not request.contact_person:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="business_name and contact_person are required for business users"
                )
            
            # Create business user
            hashed_password = get_password_hash(request.password)
            user = UserBusiness(
                email=request.email,
                business_name=request.business_name,
                contact_person=request.contact_person,
                phone=request.phone,
                hashed_password=hashed_password,
                gstin=request.gstin,
                business_category_set=settings.DEFAULT_BUSINESS_CATEGORIES
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            user_id = user.id
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_type must be 'consumer' or 'business'"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_id, "user_type": request.user_type, "email": request.email},
            expires_delta=access_token_expires
        )
        
        # Log to audit
        AuditLogger.log_action(
            db=audit_db,
            actor=AuditActor.USER,
            action=AuditAction.USER_REGISTERED,
            user_id=user_id,
            user_type=request.user_type,
            outcome="success"
        )
        
        logger.info(f"User registered: {request.email} ({request.user_type})")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user_id,
            user_type=request.user_type
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
    audit_db: Session = Depends(get_audit_db)
):
    """
    Login with email and password
    
    **Request Body:**
    - email: User's email
    - password: User's password
    - user_type: "consumer" or "business"
    
    **Returns:** JWT access token
    """
    try:
        # Authenticate user
        user = authenticate_user(db, request.email, request.password, request.user_type)
        
        if not user:
            AuditLogger.log_action(
                db=audit_db,
                actor=AuditActor.USER,
                action=AuditAction.USER_LOGIN,
                user_id=None,
                user_type=request.user_type,
                outcome="failed",
                metadata={"email": request.email}
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id, "user_type": request.user_type, "email": user.email},
            expires_delta=access_token_expires
        )
        
        # Log to audit
        AuditLogger.log_action(
            db=audit_db,
            actor=AuditActor.USER,
            action=AuditAction.USER_LOGIN,
            user_id=user.id,
            user_type=request.user_type,
            outcome="success"
        )
        
        logger.info(f"User logged in: {request.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            user_type=request.user_type
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout")
async def logout(
    current_user=Depends(get_current_user),
    audit_db: Session = Depends(get_audit_db)
):
    """
    Logout current user
    
    **Requires:** JWT Bearer token in Authorization header
    """
    try:
        user = current_user["user"]
        user_type = current_user["user_type"]
        
        # Log to audit
        AuditLogger.log_action(
            db=audit_db,
            actor=AuditActor.USER,
            action=AuditAction.USER_LOGOUT,
            user_id=user.id,
            user_type=user_type,
            outcome="success"
        )
        
        logger.info(f"User logged out: {user.email}")
        
        return {"message": "Logged out successfully"}
    
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )
