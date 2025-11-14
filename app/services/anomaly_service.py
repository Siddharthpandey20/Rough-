"""
Anomaly Detection Service using Isolation Forest and Statistical Methods
"""

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import pickle
import os
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.transaction import Transaction
from app.models.pattern import Pattern

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Anomaly Detection Service"""
    
    def __init__(self):
        self.models = {}  # Per-user models
        self.scalers = {}  # Per-user scalers
        self.model_dir = "data/models"
        os.makedirs(self.model_dir, exist_ok=True)
    
    def train_user_model(
        self,
        user_id: int,
        user_type: str,
        transactions: List[Transaction]
    ) -> bool:
        """
        Train Isolation Forest model for a specific user
        
        Args:
            user_id: User ID
            user_type: 'consumer' or 'business'
            transactions: Historical transactions
        
        Returns: True if training successful
        """
        try:
            if len(transactions) < 30:
                logger.warning(f"Insufficient data for user {user_id}. Need at least 30 transactions.")
                return False
            
            # Extract features
            features = self._extract_features(transactions)
            
            if features is None or len(features) == 0:
                return False
            
            # Scale features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Train Isolation Forest
            model = IsolationForest(
                contamination=settings.ISOLATION_FOREST_CONTAMINATION,
                random_state=42,
                n_estimators=100
            )
            model.fit(features_scaled)
            
            # Save model and scaler
            model_key = f"{user_type}_{user_id}"
            self.models[model_key] = model
            self.scalers[model_key] = scaler
            
            # Persist to disk
            self._save_model(model_key, model, scaler)
            
            logger.info(f"Trained anomaly model for user {user_id} with {len(transactions)} transactions")
            return True
        
        except Exception as e:
            logger.error(f"Model training error: {e}")
            return False
    
    def detect_anomaly(
        self,
        user_id: int,
        user_type: str,
        transaction: Transaction,
        pattern: Pattern,
        db: Session
    ) -> Tuple[bool, float, str]:
        """
        Detect if transaction is anomalous
        
        Returns: (is_anomaly, anomaly_score, reason)
        """
        try:
            model_key = f"{user_type}_{user_id}"
            
            # Load model if not in memory
            if model_key not in self.models:
                self._load_model(model_key)
            
            # Extract features for single transaction
            features = self._extract_single_transaction_features(transaction)
            
            if features is None:
                return False, 0.0, "Could not extract features"
            
            # Initialize results
            is_anomaly = False
            anomaly_score = 0.0
            reasons = []
            
            # 1. Isolation Forest Detection (if model exists)
            if model_key in self.models:
                model = self.models[model_key]
                scaler = self.scalers[model_key]
                
                features_scaled = scaler.transform(features)
                prediction = model.predict(features_scaled)[0]
                if_score = model.score_samples(features_scaled)[0]
                
                if prediction == -1:  # Anomaly detected
                    reasons.append("Isolation Forest flagged as outlier")
                    anomaly_score = max(anomaly_score, 0.7)
                    is_anomaly = True
            
            # 2. Statistical Sigma Rule
            if pattern and pattern.avg_monthly_spend > 0:
                amount = transaction.amount
                mean = pattern.avg_monthly_spend
                std = pattern.std_monthly_spend
                
                if std > 0:
                    z_score = (amount - mean) / std
                    
                    # 3-sigma rule
                    if z_score > settings.SIGMA_THRESHOLD:
                        reasons.append(f"Amount exceeds {settings.SIGMA_THRESHOLD}σ threshold (z-score: {z_score:.2f})")
                        anomaly_score = max(anomaly_score, 0.6)
                        is_anomaly = True
                    
                    # 6-sigma rule (high confidence)
                    if z_score > settings.HIGH_CONFIDENCE_SIGMA:
                        reasons.append(f"Amount significantly exceeds normal (z-score: {z_score:.2f})")
                        anomaly_score = max(anomaly_score, 0.9)
                        is_anomaly = True
            
            # 3. Check for unusual time patterns
            hour = transaction.date.hour
            day_of_week = transaction.date.weekday()
            
            # Check if transaction is during unusual hours (e.g., 2-5 AM)
            if hour >= 2 and hour <= 5:
                reasons.append("Transaction at unusual hour (2-5 AM)")
                anomaly_score = max(anomaly_score, 0.5)
                is_anomaly = True
            
            # 4. Check for duplicate invoice numbers
            if transaction.invoice_no:
                duplicate = db.query(Transaction).filter(
                    Transaction.invoice_no == transaction.invoice_no,
                    Transaction.id != transaction.id,
                    Transaction.user_consumer_id == user_id if user_type == "consumer" else Transaction.user_business_id == user_id
                ).first()
                
                if duplicate:
                    reasons.append("Duplicate invoice number detected")
                    anomaly_score = max(anomaly_score, 0.8)
                    is_anomaly = True
            
            # Combine reasons
            reason = "; ".join(reasons) if reasons else "No anomalies detected"
            
            logger.info(f"Anomaly detection for transaction {transaction.id}: {is_anomaly} (score: {anomaly_score:.2f})")
            return is_anomaly, anomaly_score, reason
        
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return False, 0.0, f"Detection error: {str(e)}"
    
    def _extract_features(self, transactions: List[Transaction]) -> np.ndarray:
        """Extract feature matrix from transactions"""
        try:
            features = []
            
            for tx in transactions:
                feature_vector = [
                    tx.amount,
                    tx.date.hour,
                    tx.date.weekday(),
                    tx.date.day,
                    1 if tx.payment_channel.value == "UPI" else 0,
                    1 if tx.payment_channel.value == "Card" else 0,
                    1 if tx.payment_channel.value == "Cash" else 0,
                    tx.ocr_confidence,
                ]
                features.append(feature_vector)
            
            return np.array(features)
        
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None
    
    def _extract_single_transaction_features(self, transaction: Transaction) -> np.ndarray:
        """Extract features for a single transaction"""
        try:
            feature_vector = [
                transaction.amount,
                transaction.date.hour,
                transaction.date.weekday(),
                transaction.date.day,
                1 if transaction.payment_channel.value == "UPI" else 0,
                1 if transaction.payment_channel.value == "Card" else 0,
                1 if transaction.payment_channel.value == "Cash" else 0,
                transaction.ocr_confidence,
            ]
            
            return np.array([feature_vector])
        
        except Exception as e:
            logger.error(f"Single feature extraction error: {e}")
            return None
    
    def _save_model(self, model_key: str, model, scaler):
        """Save model and scaler to disk"""
        try:
            model_path = os.path.join(self.model_dir, f"{model_key}_model.pkl")
            scaler_path = os.path.join(self.model_dir, f"{model_key}_scaler.pkl")
            
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
            
            logger.info(f"Saved model: {model_key}")
        
        except Exception as e:
            logger.error(f"Model save error: {e}")
    
    def _load_model(self, model_key: str):
        """Load model and scaler from disk"""
        try:
            model_path = os.path.join(self.model_dir, f"{model_key}_model.pkl")
            scaler_path = os.path.join(self.model_dir, f"{model_key}_scaler.pkl")
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                with open(model_path, 'rb') as f:
                    self.models[model_key] = pickle.load(f)
                
                with open(scaler_path, 'rb') as f:
                    self.scalers[model_key] = pickle.load(f)
                
                logger.info(f"Loaded model: {model_key}")
            else:
                logger.warning(f"Model not found: {model_key}")
        
        except Exception as e:
            logger.error(f"Model load error: {e}")
    
    def update_patterns(
        self,
        db: Session,
        user_id: int,
        user_type: str,
        category: str
    ):
        """Update spending patterns for a user-category combination"""
        try:
            # Get transactions for this user and category (last 90 days)
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            if user_type == "consumer":
                transactions = db.query(Transaction).filter(
                    Transaction.user_consumer_id == user_id,
                    Transaction.category == category,
                    Transaction.date >= cutoff_date,
                    Transaction.confirmed != False  # Exclude rejected transactions
                ).all()
            else:
                transactions = db.query(Transaction).filter(
                    Transaction.user_business_id == user_id,
                    Transaction.category == category,
                    Transaction.date >= cutoff_date,
                    Transaction.confirmed != False
                ).all()
            
            if not transactions:
                return
            
            # Calculate statistics
            amounts = [tx.amount for tx in transactions]
            avg_monthly = np.mean(amounts)
            std_monthly = np.std(amounts)
            
            # Get or create pattern
            if user_type == "consumer":
                pattern = db.query(Pattern).filter(
                    Pattern.user_consumer_id == user_id,
                    Pattern.category_id == category
                ).first()
            else:
                pattern = db.query(Pattern).filter(
                    Pattern.user_business_id == user_id,
                    Pattern.category_id == category
                ).first()
            
            if not pattern:
                pattern = Pattern(
                    user_consumer_id=user_id if user_type == "consumer" else None,
                    user_business_id=user_id if user_type == "business" else None,
                    category_id=category
                )
                db.add(pattern)
            
            # Update pattern
            pattern.avg_monthly_spend = avg_monthly
            pattern.std_monthly_spend = std_monthly
            pattern.avg_weekly_spend = avg_monthly / 4.33  # Approximate
            pattern.std_weekly_spend = std_monthly / 4.33
            pattern.sample_count = len(transactions)
            pattern.upper_threshold_3sigma = avg_monthly + (3 * std_monthly)
            pattern.upper_threshold_6sigma = avg_monthly + (6 * std_monthly)
            pattern.last_update = datetime.utcnow()
            
            db.commit()
            logger.info(f"Updated pattern for user {user_id}, category {category}")
        
        except Exception as e:
            logger.error(f"Pattern update error: {e}")
            db.rollback()


# Global instance
anomaly_detector = AnomalyDetector()
