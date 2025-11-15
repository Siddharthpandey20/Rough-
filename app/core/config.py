"""
Application Configuration
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "LUMEN"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str
    DATABASE_AUDIT_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Gemini API
    GEMINI_API_KEY: str
    
    # Encryption
    MASTER_ENCRYPTION_KEY: str
    
    # Gmail
    GMAIL_CREDENTIALS_PATH: str = "credentials/gmail_credentials.json"
    GMAIL_TOKEN_PATH: str = "credentials/gmail_token.json"
    
    # OCR
    TESSERACT_PATH: str = "/usr/bin/tesseract"
    OCR_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Anomaly Detection
    ISOLATION_FOREST_CONTAMINATION: float = 0.02
    SIGMA_THRESHOLD: float = 3.0
    HIGH_CONFIDENCE_SIGMA: float = 6.0
    ANOMALY_CONFIDENCE_THRESHOLD: float = 0.85
    
    # RAG
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_STORE_PATH: str = "data/vector_store"
    FAISS_INDEX_PATH: str = "data/faiss_index"
    RAG_TOP_K: int = 5
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "data/uploads"
    ENCRYPTED_STORAGE_DIR: str = "data/encrypted"
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:5173"]
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Split comma-separated string into list
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    # Categories
    DEFAULT_CONSUMER_CATEGORIES: List[str] = [
        "Groceries",
        "Food & Dining",
        "Transport",
        "Utilities",
        "Entertainment"
    ]
    
    DEFAULT_BUSINESS_CATEGORIES: List[str] = [
        "Inventory",
        "Supplies",
        "Travel",
        "Services",
        "Salary"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env (like old TWILIO vars)


# Create settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.ENCRYPTED_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
os.makedirs(os.path.dirname(settings.FAISS_INDEX_PATH), exist_ok=True)
os.makedirs("credentials", exist_ok=True)
os.makedirs("logs", exist_ok=True)
