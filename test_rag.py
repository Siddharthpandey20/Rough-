"""
Test RAG Service functionality
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import engine, SessionLocal
from app.models.user import UserConsumer
from app.models.transaction import Transaction
from app.services.rag_service import rag_service
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_rag_dependencies():
    """Test if RAG dependencies are available"""
    print("\n" + "=" * 60)
    print("Testing RAG Dependencies")
    print("=" * 60)
    
    # Test sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
        print("✓ sentence-transformers: AVAILABLE")
    except ImportError as e:
        print(f"✗ sentence-transformers: NOT AVAILABLE - {e}")
        return False
    
    # Test faiss
    try:
        import faiss
        print(f"✓ faiss: AVAILABLE (version {faiss.__version__})")
    except ImportError as e:
        print(f"✗ faiss: NOT AVAILABLE - {e}")
        return False
    
    return True

def test_embedding_model():
    """Test if embedding model loads correctly"""
    print("\n" + "=" * 60)
    print("Testing Embedding Model")
    print("=" * 60)
    
    try:
        model = rag_service.embedding_model
        if model is None:
            print("✗ Embedding model failed to load")
            return False
        
        print(f"✓ Embedding model loaded successfully")
        print(f"  Model: {rag_service._embedding_model}")
        print(f"  Dimension: {rag_service.embedding_dim}")
        
        # Test encoding
        test_text = "Test transaction: Paid ₹500 to Starbucks"
        embedding = model.encode(test_text)
        print(f"✓ Test encoding successful")
        print(f"  Embedding shape: {embedding.shape}")
        
        return True
    except Exception as e:
        print(f"✗ Embedding model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transaction_indexing():
    """Test transaction indexing"""
    print("\n" + "=" * 60)
    print("Testing Transaction Indexing")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Get first consumer user
        user = db.query(UserConsumer).first()
        if not user:
            print("✗ No consumer user found. Please create a user first.")
            return False
        
        print(f"✓ Using user: {user.email} (ID: {user.id})")
        
        # Get transactions for this user
        transactions = db.query(Transaction).filter(
            Transaction.user_consumer_id == user.id
        ).limit(5).all()
        
        if not transactions:
            print("✗ No transactions found for user. Please create transactions first.")
            return False
        
        print(f"✓ Found {len(transactions)} transactions")
        
        # Test indexing each transaction
        indexed_count = 0
        for tx in transactions:
            try:
                rag_service.index_transaction(db, tx, user.id, "consumer")
                indexed_count += 1
                print(f"✓ Indexed transaction {tx.id}: ₹{tx.amount} at {tx.merchant_name_raw}")
            except Exception as e:
                print(f"✗ Failed to index transaction {tx.id}: {e}")
        
        db.commit()
        print(f"\n✓ Successfully indexed {indexed_count}/{len(transactions)} transactions")
        
        return indexed_count > 0
    
    except Exception as e:
        print(f"✗ Transaction indexing test failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

def test_context_retrieval():
    """Test context retrieval"""
    print("\n" + "=" * 60)
    print("Testing Context Retrieval")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Get first consumer user
        user = db.query(UserConsumer).first()
        if not user:
            print("✗ No consumer user found")
            return False
        
        print(f"✓ Using user: {user.email} (ID: {user.id})")
        
        # Test queries
        test_queries = [
            "Show me my grocery expenses",
            "How much did I spend on food?",
            "What transactions did I make last month?",
            "Tell me about my recent purchases"
        ]
        
        for query in test_queries:
            print(f"\n📝 Query: {query}")
            
            try:
                context = rag_service.retrieve_context(
                    query=query,
                    user_id=user.id,
                    user_type="consumer",
                    db=db,
                    top_k=3
                )
                
                if context:
                    print(f"✓ Retrieved {len(context)} relevant documents:")
                    for i, doc in enumerate(context, 1):
                        print(f"  {i}. {doc['summary']} (relevance: {doc['relevance_score']:.3f})")
                else:
                    print("  No relevant documents found")
                
            except Exception as e:
                print(f"✗ Retrieval failed: {e}")
        
        return True
    
    except Exception as e:
        print(f"✗ Context retrieval test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_exact_lookup():
    """Test exact database lookup"""
    print("\n" + "=" * 60)
    print("Testing Exact Lookup")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Get first consumer user
        user = db.query(UserConsumer).first()
        if not user:
            print("✗ No consumer user found")
            return False
        
        # Get a sample transaction
        tx = db.query(Transaction).filter(
            Transaction.user_consumer_id == user.id
        ).first()
        
        if not tx:
            print("✗ No transactions found")
            return False
        
        print(f"✓ Testing with transaction: ₹{tx.amount} at {tx.merchant_name_raw}")
        
        # Test lookup by merchant
        results = rag_service.exact_lookup(
            db=db,
            user_id=user.id,
            user_type="consumer",
            merchant_name=tx.merchant_name_raw
        )
        
        print(f"✓ Merchant lookup found {len(results)} matches")
        
        # Test lookup by amount
        results = rag_service.exact_lookup(
            db=db,
            user_id=user.id,
            user_type="consumer",
            amount=tx.amount
        )
        
        print(f"✓ Amount lookup found {len(results)} matches")
        
        return True
    
    except Exception as e:
        print(f"✗ Exact lookup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("RAG SERVICE TEST SUITE")
    print("=" * 60)
    
    results = {
        "Dependencies": test_rag_dependencies(),
        "Embedding Model": test_embedding_model(),
        "Transaction Indexing": test_transaction_indexing(),
        "Context Retrieval": test_context_retrieval(),
        "Exact Lookup": test_exact_lookup()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! RAG service is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
