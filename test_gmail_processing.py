
Direct test of Gmail transaction processing
Tests the full pipeline from email parsing to database insertion
"""

import sys
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.gmail_monitor_service import gmail_monitor
from app.core.database import SessionLocal
from app.models.transaction import Transaction

def test_gmail_processing():
    """Test Gmail processing end-to-end"""
    print("=" * 70)
    print("Testing Gmail Transaction Processing")
    print("=" * 70)
    
    # Check authentication
    token_path = "credentials/gmail_token.json_1"
    if not os.path.exists(token_path):
        print("\n❌ Gmail token not found!")
        print("Run: python test_gmail_auth.py")
        return False
    
    print(f"\n✅ Gmail token found: {token_path}")
    
    # Authenticate
    print("\n🔐 Authenticating Gmail...")
    if not gmail_monitor._authenticate():
        print("❌ Authentication failed!")
        return False
    
    print("✅ Gmail authenticated successfully")
    
    # Check for unread emails
    print("\n📧 Checking for unread transaction emails...")
    try:
        query = 'is:unread (payment OR transaction OR receipt OR invoice OR UPI OR IMPS OR NEFT OR debited OR credited OR bank OR "Rs." OR "INR" OR "₹")'
        results = gmail_monitor.gmail_service.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=5
        ).execute()
        
        messages = results.get('messages', [])
        print(f"📬 Found {len(messages)} unread transaction-related emails")
        
        if not messages:
            print("\n⚠️ No unread transaction emails found")
            print("💡 Send a test payment email to your inbox")
            return False
        
        # Process first email
        message_id = messages[0]['id']
        print(f"\n🔍 Testing with message: {message_id}")
        print("-" * 70)
        
        # Parse the email
        print("\n📄 Step 1: Parsing email...")
        transaction_data = gmail_monitor.gmail_service._parse_email_message(message_id)
        
        if not transaction_data:
            print("❌ Failed to extract transaction data")
            return False
        
        print(f"✅ Email parsed successfully")
        print(f"📊 Extracted data:")
        print(f"   - Amount: ₹{transaction_data.get('amount', 'N/A')}")
        print(f"   - Merchant: {transaction_data.get('merchant', 'N/A')}")
        print(f"   - Type: {transaction_data.get('transaction_type', 'N/A')}")
        print(f"   - Method: {transaction_data.get('payment_method', 'N/A')}")
        print(f"   - Confidence: {transaction_data.get('gemini_confidence', 'N/A')}")
        
        # Check database before
        print("\n💾 Step 2: Checking database...")
        db = SessionLocal()
        try:
            count_before = db.query(Transaction).filter(
                Transaction.source_type == 'GMAIL'
            ).count()
            print(f"📊 Transactions in database (before): {count_before}")
        finally:
            db.close()
        
        # Process the message
        print("\n⚙️ Step 3: Processing message (database insertion)...")
        success = gmail_monitor._process_email_message(message_id)
        
        if not success:
            print("❌ Failed to process message")
            return False
        
        # Check database after
        print("\n✅ Step 4: Verifying database insertion...")
        db = SessionLocal()
        try:
            count_after = db.query(Transaction).filter(
                Transaction.source_type == 'GMAIL'
            ).count()
            print(f"📊 Transactions in database (after): {count_after}")
            
            if count_after > count_before:
                print(f"✅ SUCCESS! {count_after - count_before} new transaction(s) added")
                
                # Show the latest transaction
                latest = db.query(Transaction).filter(
                    Transaction.source_type == 'GMAIL'
                ).order_by(Transaction.created_at.desc()).first()
                
                if latest:
                    print(f"\n📝 Latest transaction:")
                    print(f"   - ID: {latest.id}")
                    print(f"   - Amount: ₹{latest.amount}")
                    print(f"   - Merchant: {latest.merchant_name_raw}")
                    print(f"   - Category: {latest.category}")
                    print(f"   - Date: {latest.date}")
                    print(f"   - Created: {latest.created_at}")
                
                return True
            else:
                print("❌ FAILED! Transaction was not saved to database")
                print("💡 Check logs above for errors")
                return False
                
        finally:
            db.close()
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Gmail Transaction Processing Test")
    print("=" * 70)
    print("\nThis script will:")
    print("1. Authenticate with Gmail")
    print("2. Find an unread transaction email")
    print("3. Parse it with Gemini AI")
    print("4. Insert it into the database")
    print("5. Verify the insertion")
    print("\n" + "=" * 70)
    
    input("\nPress Enter to start the test...")
    
    success = test_gmail_processing()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ALL TESTS PASSED")
        print("Gmail transaction processing is working correctly!")
    else:
        print("❌ TEST FAILED")
        print("Check the logs above for details")
    print("=" * 70)
    
    exit(0 if success else 1)
