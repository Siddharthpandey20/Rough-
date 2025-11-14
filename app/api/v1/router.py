"""
API Router - Main router for all v1 endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, transactions, chat, ingestion, anomalies

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat & RAG"])
api_router.include_router(ingestion.router, prefix="/ingest", tags=["Data Ingestion"])
api_router.include_router(anomalies.router, prefix="/anomalies", tags=["Anomaly Detection"])
