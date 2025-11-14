"""
Reindex all existing transactions for RAG
Run this to index transactions that were created before RAG was fixed
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import UserConsumer, UserBusiness
from app.models.transaction import Transaction
from app.services.rag_service import rag_service
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reindex_consumer_transactions():
    """Reindex all consumer transactions"""
    db = SessionLocal()
    try:
        users = db.query(UserConsumer).all()
        print(f"\n📊 Found {len(users)} consumer users")
        
        total_indexed = 0
        
        for user in users:
            print(f"\n👤 Processing user: {user.email} (ID: {user.id})")
            
            transactions = db.query(Transaction).filter(
                Transaction.user_consumer_id == user.id
            ).all()
            
            print(f"   Found {len(transactions)} transactions")
            
            indexed_count = 0
            for tx in transactions:
                try:
                    rag_service.index_transaction(db, tx, user.id, "consumer")
                    indexed_count += 1
                    
                    if indexed_count % 10 == 0:
                        print(f"   Indexed {indexed_count}/{len(transactions)}...")
                
                except Exception as e:
                    logger.error(f"   Failed to index transaction {tx.id}: {e}")
            
            print(f"   ✓ Indexed {indexed_count}/{len(transactions)} transactions")
            total_indexed += indexed_count
            
            # Commit after each user
            db.commit()
        
        return total_indexed
    
    except Exception as e:
        logger.error(f"Error reindexing consumer transactions: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

def reindex_business_transactions():
    """Reindex all business transactions"""
    db = SessionLocal()
    try:
        users = db.query(UserBusiness).all()
        print(f"\n🏢 Found {len(users)} business users")
        
        total_indexed = 0
        
        for user in users:
            print(f"\n👤 Processing user: {user.email} (ID: {user.id})")
            
            transactions = db.query(Transaction).filter(
                Transaction.user_business_id == user.id
            ).all()
            
            print(f"   Found {len(transactions)} transactions")
            
            indexed_count = 0
            for tx in transactions:
                try:
                    rag_service.index_transaction(db, tx, user.id, "business")
                    indexed_count += 1
                    
                    if indexed_count % 10 == 0:
                        print(f"   Indexed {indexed_count}/{len(transactions)}...")
                
                except Exception as e:
                    logger.error(f"   Failed to index transaction {tx.id}: {e}")
            
            print(f"   ✓ Indexed {indexed_count}/{len(transactions)} transactions")
            total_indexed += indexed_count
            
            # Commit after each user
            db.commit()
        
        return total_indexed
    
    except Exception as e:
        logger.error(f"Error reindexing business transactions: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

def main():
    """Main reindexing function"""
    print("\n" + "=" * 60)
    print("RAG REINDEXING - All Existing Transactions")
    print("=" * 60)
    
    print("\nThis will index all existing transactions for RAG retrieval.")
    print("This may take a few minutes depending on transaction volume.")
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    # Reindex consumers
    consumer_count = reindex_consumer_transactions()
    
    # Reindex businesses
    business_count = reindex_business_transactions()
    
    # Summary
    print("\n" + "=" * 60)
    print("REINDEXING COMPLETE")
    print("=" * 60)
    print(f"Consumer transactions indexed: {consumer_count}")
    print(f"Business transactions indexed: {business_count}")
    print(f"Total transactions indexed: {consumer_count + business_count}")
    print("\n✅ All transactions are now indexed for RAG!")
    print("Users can now query their transactions via the chat interface.")
    print("=" * 60)

if __name__ == "__main__":
    main()
