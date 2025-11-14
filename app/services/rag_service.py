"""
RAG (Retrieval-Augmented Generation) Service
Implements stateful chatbot with hybrid retrieval
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
import json
import os
import logging
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.config import settings
from app.models.transaction import Transaction
from app.models.chat import ChatSession, ChatMemory, ChatMessage
from app.models.rag import RAGIndex
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

# Lazy imports for heavy dependencies
_sentence_transformers_imported = False
_faiss_imported = False

def _import_sentence_transformers():
    """Lazy import of sentence_transformers"""
    global _sentence_transformers_imported, SentenceTransformer
    if not _sentence_transformers_imported:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformers_imported = True
            logger.info("sentence_transformers imported successfully")
        except Exception as e:
            logger.error(f"Failed to import sentence_transformers: {e}")
            SentenceTransformer = None
    return SentenceTransformer

def _import_faiss():
    """Lazy import of faiss"""
    global _faiss_imported, faiss
    if not _faiss_imported:
        try:
            import faiss
            _faiss_imported = True
            logger.info("faiss imported successfully")
        except Exception as e:
            logger.error(f"Failed to import faiss: {e}")
            faiss = None
    return faiss


class RAGService:
    """RAG Service for stateful chatbot"""
    
    def __init__(self):
        # Lazy load embedding model (only when first needed)
        self._embedding_model = None
        self.embedding_dim = 384  # Default dimension for all-MiniLM-L6-v2
        
        # FAISS indices (per user)
        self.indices = {}
        self.doc_mappings = {}  # {user_key: {faiss_id: doc_id}}
        
        # Ensure directories exist
        os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
        os.makedirs(os.path.dirname(settings.FAISS_INDEX_PATH), exist_ok=True)
    
    @property
    def embedding_model(self):
        """Lazy load the embedding model on first use"""
        if self._embedding_model is None:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            try:
                SentenceTransformer = _import_sentence_transformers()
                if SentenceTransformer is None:
                    raise ImportError("sentence_transformers not available")
                
                self._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
                self.embedding_dim = self._embedding_model.get_sentence_embedding_dimension()
                logger.info(f"Embedding model loaded successfully (dim={self.embedding_dim})")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                logger.warning("RAG functionality will be limited - continuing without embeddings")
                # Return None to indicate model not available
                self._embedding_model = "unavailable"
        
        return self._embedding_model if self._embedding_model != "unavailable" else None
    
    def index_transaction(
        self,
        db: Session,
        transaction: Transaction,
        user_id: int,
        user_type: str
    ):
        """Index a transaction for RAG retrieval"""
        try:
            # Create document summary
            doc_content = self._create_transaction_summary(transaction)
            doc_summary = f"Transaction of ₹{transaction.amount} at {transaction.merchant_name_raw} on {transaction.date.strftime('%Y-%m-%d')}"
            
            # Generate embedding
            embedding = self.embedding_model.encode(doc_content)
            
            # Create RAG index entry
            doc_id = f"tx_{transaction.id}_{datetime.utcnow().timestamp()}"
            
            rag_index = RAGIndex(
                doc_id=doc_id,
                transaction_id=transaction.id,
                user_consumer_id=user_id if user_type == "consumer" else None,
                user_business_id=user_id if user_type == "business" else None,
                doc_type="transaction",
                doc_summary=doc_summary,
                doc_content=doc_content,
                embedding_model=settings.EMBEDDING_MODEL,
                index_metadata={
                    "amount": transaction.amount,
                    "category": transaction.category,
                    "date": transaction.date.isoformat()
                }
            )
            
            db.add(rag_index)
            db.commit()
            
            # Add to FAISS index
            self._add_to_faiss(user_id, user_type, doc_id, embedding)
            
            logger.info(f"Indexed transaction {transaction.id}")
        
        except Exception as e:
            logger.error(f"Transaction indexing error: {e}")
            db.rollback()
    
    def retrieve_context(
        self,
        query: str,
        user_id: int,
        user_type: str,
        db: Session,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant documents for a query using hybrid retrieval
        
        Returns: List of relevant transaction summaries
        """
        try:
            # Check if embedding model is available
            if self.embedding_model is None:
                logger.warning("Embedding model not available, returning empty context")
                return []
            
            # Import FAISS lazily
            faiss_module = _import_faiss()
            if faiss_module is None:
                logger.warning("FAISS not available, returning empty context")
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Retrieve from FAISS
            user_key = f"{user_type}_{user_id}"
            retrieved_docs = []
            
            # Load index if not in memory
            if user_key not in self.indices:
                self._load_index(user_key)
            
            if user_key in self.indices:
                index = self.indices[user_key]
                doc_mapping = self.doc_mappings[user_key]
                
                # Search
                distances, indices = index.search(np.array([query_embedding]), min(top_k, index.ntotal))
                
                for dist, idx in zip(distances[0], indices[0]):
                    if idx != -1 and idx in doc_mapping:  # -1 means no result
                        doc_id = doc_mapping[idx]
                        
                        # Fetch from database
                        rag_doc = db.query(RAGIndex).filter(RAGIndex.doc_id == doc_id).first()
                        
                        if rag_doc and rag_doc.transaction_id:
                            transaction = db.query(Transaction).filter(Transaction.id == rag_doc.transaction_id).first()
                            
                            if transaction:
                                retrieved_docs.append({
                                    "id": transaction.id,
                                    "amount": transaction.amount,
                                    "merchant": transaction.merchant_name_raw,
                                    "category": transaction.category,
                                    "date": transaction.date.isoformat(),
                                    "payment_channel": transaction.payment_channel.value,
                                    "summary": rag_doc.doc_summary,
                                    "relevance_score": float(1.0 / (1.0 + dist))  # Convert distance to similarity
                                })
            
            logger.info(f"Retrieved {len(retrieved_docs)} documents for query")
            return retrieved_docs
        
        except Exception as e:
            logger.error(f"Context retrieval error: {e}")
            return []
    
    def exact_lookup(
        self,
        db: Session,
        user_id: int,
        user_type: str,
        merchant_name: Optional[str] = None,
        amount: Optional[float] = None,
        amount_tolerance: float = 0.02,
        date: Optional[datetime] = None,
        date_tolerance_days: int = 1
    ) -> List[Dict]:
        """
        Perform exact database lookup for transactions
        
        Returns: List of matching transactions
        """
        try:
            # Build query
            if user_type == "consumer":
                query = db.query(Transaction).filter(Transaction.user_consumer_id == user_id)
            else:
                query = db.query(Transaction).filter(Transaction.user_business_id == user_id)
            
            # Apply filters
            if merchant_name:
                # Fuzzy match on merchant name
                query = query.filter(Transaction.merchant_name_raw.ilike(f"%{merchant_name}%"))
            
            if amount is not None:
                # Amount with tolerance
                min_amount = amount * (1 - amount_tolerance)
                max_amount = amount * (1 + amount_tolerance)
                query = query.filter(
                    Transaction.amount >= min_amount,
                    Transaction.amount <= max_amount
                )
            
            if date:
                # Date with tolerance
                from datetime import timedelta
                start_date = date - timedelta(days=date_tolerance_days)
                end_date = date + timedelta(days=date_tolerance_days)
                query = query.filter(
                    Transaction.date >= start_date,
                    Transaction.date <= end_date
                )
            
            # Execute query
            transactions = query.all()
            
            # Format results
            results = []
            for tx in transactions:
                results.append({
                    "id": tx.id,
                    "amount": tx.amount,
                    "merchant": tx.merchant_name_raw,
                    "category": tx.category,
                    "date": tx.date.isoformat(),
                    "payment_channel": tx.payment_channel.value,
                    "invoice_no": tx.invoice_no,
                    "exact_match": True
                })
            
            logger.info(f"Exact lookup found {len(results)} matches")
            return results
        
        except Exception as e:
            logger.error(f"Exact lookup error: {e}")
            return []
    
    def get_or_create_session(
        self,
        db: Session,
        user_id: int,
        user_type: str,
        session_id: Optional[int] = None
    ) -> ChatSession:
        """Get existing or create new chat session"""
        try:
            if session_id:
                session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
                if session:
                    return session
            
            # Create new session
            session = ChatSession(
                user_consumer_id=user_id if user_type == "consumer" else None,
                user_business_id=user_id if user_type == "business" else None,
                session_metadata={"created_at": datetime.utcnow().isoformat()},
                ephemeral_memory={},
                persistent_memory_refs=[]
            )
            
            db.add(session)
            db.commit()
            db.refresh(session)
            
            logger.info(f"Created new chat session {session.id} for user {user_id}")
            return session
        
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            db.rollback()
            raise
    
    def get_persistent_memory(
        self,
        db: Session,
        user_id: int,
        user_type: str
    ) -> Dict:
        """Retrieve persistent user memory"""
        try:
            if user_type == "consumer":
                memories = db.query(ChatMemory).filter(
                    ChatMemory.user_consumer_id == user_id,
                    ChatMemory.visibility == "persistent"
                ).all()
            else:
                memories = db.query(ChatMemory).filter(
                    ChatMemory.user_business_id == user_id,
                    ChatMemory.visibility == "persistent"
                ).all()
            
            memory_dict = {mem.key: mem.value for mem in memories}
            return memory_dict
        
        except Exception as e:
            logger.error(f"Memory retrieval error: {e}")
            return {}
    
    def _create_transaction_summary(self, transaction: Transaction) -> str:
        """Create searchable text summary of transaction"""
        summary = f"""
Transaction ID: {transaction.id}
Amount: ₹{transaction.amount} {transaction.currency}
Merchant: {transaction.merchant_name_raw}
Category: {transaction.category}
Date: {transaction.date.strftime('%Y-%m-%d %H:%M')}
Payment Channel: {transaction.payment_channel.value}
Source: {transaction.source_type.value}
        """.strip()
        
        if transaction.invoice_no:
            summary += f"\nInvoice: {transaction.invoice_no}"
        
        return summary
    
    def _add_to_faiss(self, user_id: int, user_type: str, doc_id: str, embedding: np.ndarray):
        """Add document to FAISS index"""
        try:
            # Import FAISS lazily
            faiss_module = _import_faiss()
            if faiss_module is None:
                logger.warning("FAISS not available, skipping indexing")
                return
            
            user_key = f"{user_type}_{user_id}"
            
            # Create index if doesn't exist
            if user_key not in self.indices:
                self.indices[user_key] = faiss_module.IndexFlatL2(self.embedding_dim)
                self.doc_mappings[user_key] = {}
            
            # Add to index
            index = self.indices[user_key]
            faiss_id = index.ntotal
            index.add(np.array([embedding]))
            
            # Store mapping
            self.doc_mappings[user_key][faiss_id] = doc_id
            
            # Persist index periodically (every 10 documents)
            if index.ntotal % 10 == 0:
                self._save_index(user_key)
        
        except Exception as e:
            logger.error(f"FAISS add error: {e}")
    
    def _save_index(self, user_key: str):
        """Save FAISS index to disk"""
        try:
            faiss_module = _import_faiss()
            if faiss_module is None:
                return
            
            index_path = os.path.join(settings.VECTOR_STORE_PATH, f"{user_key}.faiss")
            mapping_path = os.path.join(settings.VECTOR_STORE_PATH, f"{user_key}_mapping.json")
            
            faiss_module.write_index(self.indices[user_key], index_path)
            
            with open(mapping_path, 'w') as f:
                # Convert int keys to strings for JSON
                json_mapping = {str(k): v for k, v in self.doc_mappings[user_key].items()}
                json.dump(json_mapping, f)
            
            logger.info(f"Saved FAISS index for {user_key}")
        
        except Exception as e:
            logger.error(f"Index save error: {e}")
    
    def _load_index(self, user_key: str):
        """Load FAISS index from disk"""
        try:
            faiss_module = _import_faiss()
            if faiss_module is None:
                return
            
            index_path = os.path.join(settings.VECTOR_STORE_PATH, f"{user_key}.faiss")
            mapping_path = os.path.join(settings.VECTOR_STORE_PATH, f"{user_key}_mapping.json")
            
            if os.path.exists(index_path) and os.path.exists(mapping_path):
                self.indices[user_key] = faiss_module.read_index(index_path)
                
                with open(mapping_path, 'r') as f:
                    json_mapping = json.load(f)
                    # Convert string keys back to int
                    self.doc_mappings[user_key] = {int(k): v for k, v in json_mapping.items()}
                
                logger.info(f"Loaded FAISS index for {user_key}")
        
        except Exception as e:
            logger.error(f"Index load error: {e}")


# Global instance
rag_service = RAGService()
