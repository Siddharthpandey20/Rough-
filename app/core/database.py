"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Main database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Audit database engine (separate for compliance)
audit_engine = create_engine(
    settings.DATABASE_AUDIT_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AuditSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=audit_engine)

# Base class for models
Base = declarative_base()
AuditBase = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_audit_db():
    """Dependency for getting audit database session"""
    db = AuditSessionLocal()
    try:
        yield db
    finally:
        db.close()
