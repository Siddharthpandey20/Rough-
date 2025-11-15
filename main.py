"""
LUMEN - AI-Powered Financial Transaction Management System
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.core.config import settings
from app.core.database import engine, audit_engine, Base, AuditBase
from app.api.v1.router import api_router
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting LUMEN application...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Create database tables
    try:
        logger.info("Creating main database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Main database tables created successfully")
        
        logger.info("Creating audit database tables...")
        AuditBase.metadata.create_all(bind=audit_engine)
        logger.info("Audit database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        logger.error("Please ensure PostgreSQL is running and databases exist:")
        logger.error(f"  - {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'lumen_db'}")
        logger.error(f"  - {settings.DATABASE_AUDIT_URL.split('@')[1] if '@' in settings.DATABASE_AUDIT_URL else 'lumen_audit_db'}")
    
    # Start Gmail background monitoring
    try:
        logger.info("🚀 Starting Gmail background monitoring service...")
        from app.services.gmail_monitor_service import gmail_monitor
        gmail_monitor.start()
        logger.info("✅ Gmail monitoring service started successfully")
    except Exception as e:
        logger.error(f"Failed to start Gmail monitoring: {e}")
        logger.warning("Gmail monitoring will not be available. You can start it manually via /api/v1/n8n/gmail/start")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LUMEN application...")
    
    # Stop Gmail monitoring
    try:
        from app.services.gmail_monitor_service import gmail_monitor
        gmail_monitor.stop()
        logger.info("Gmail monitoring service stopped")
    except Exception as e:
        logger.error(f"Error stopping Gmail monitoring: {e}")


# Initialize FastAPI app
app = FastAPI(
    title="LUMEN API",
    description="AI-Powered Financial Transaction Management & Anomaly Detection System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS Configuration
# Allow all origins in development mode for Swagger UI to work
cors_origins = settings.CORS_ORIGINS if not settings.DEBUG else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to LUMEN API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False  # Disable reload to avoid multiprocessing issues with Python 3.13
    )
