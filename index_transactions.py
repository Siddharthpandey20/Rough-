"""
Index existing transactions into RAG system
Run this after populating demo data to enable chat functionality
"""

import sys
from app.core.database import SessionLocal
from app.models.transaction import Transaction
from app.services.rag_service import rag_service

print("=" * 60)
print("LUMEN Transaction Indexing")
print("=" * 60)

def index_all_transactions():
    """Index all existing transactions for RAG"""
    db = SessionLocal()
    
    try:
        # Get all transactions
        transactions = db.query(Transaction).all()
        
        print(f"\n📊 Found {len(transactions)} transactions to index")
        
        indexed = 0
        errors = 0
        
        for txn in transactions:
            try:
                # Determine user type
                user_id = txn.user_consumer_id if txn.user_consumer_id else txn.user_business_id
                user_type = "consumer" if txn.user_consumer_id else "business"
                
                # Index transaction
                rag_service.index_transaction(db, txn, user_id, user_type)
                indexed += 1
                
                if indexed % 10 == 0:
                    print(f"   Progress: {indexed}/{len(transactions)} indexed")
            
            except Exception as e:
                errors += 1
                print(f"   ⚠️  Error indexing transaction {txn.id}: {e}")
        
        print(f"\n✅ Indexing complete!")
        print(f"   Successfully indexed: {indexed}")
        print(f"   Errors: {errors}")
        
        db.close()
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("\n⏳ Starting transaction indexing...")
    print("   This may take a few minutes for the embedding model to load...")
    index_all_transactions()
    print("\n✨ Done! You can now use the chat feature.")
