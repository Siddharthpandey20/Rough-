"""
Test script to verify which user has transactions and start Gmail monitor for specific user

Usage:
    python test_user_transactions.py --list-users       # List all users
    python test_user_transactions.py --user-id 1        # Show transactions for User ID 1
    python test_user_transactions.py --user-id 2        # Show transactions for User ID 2
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.user import UserConsumer, UserBusiness
from app.models.transaction import Transaction
from sqlalchemy import func
import argparse


def list_users():
    """List all users in the system"""
    db = SessionLocal()
    try:
        print("\n" + "=" * 80)
        print("CONSUMER USERS")
        print("=" * 80)
        
        consumers = db.query(UserConsumer).all()
        if consumers:
            for user in consumers:
                trans_count = db.query(Transaction).filter(
                    Transaction.user_consumer_id == user.id
                ).count()
                print(f"ID: {user.id} | Email: {user.email} | Name: {user.full_name} | Transactions: {trans_count}")
        else:
            print("No consumer users found")
        
        print("\n" + "=" * 80)
        print("BUSINESS USERS")
        print("=" * 80)
        
        businesses = db.query(UserBusiness).all()
        if businesses:
            for user in businesses:
                trans_count = db.query(Transaction).filter(
                    Transaction.user_business_id == user.id
                ).count()
                print(f"ID: {user.id} | Email: {user.email} | Business: {user.business_name} | Transactions: {trans_count}")
        else:
            print("No business users found")
        
        print("=" * 80)
    finally:
        db.close()


def show_user_transactions(user_id: int):
    """Show transactions for a specific user"""
    db = SessionLocal()
    try:
        # Try to find as consumer
        consumer = db.query(UserConsumer).filter(UserConsumer.id == user_id).first()
        business = db.query(UserBusiness).filter(UserBusiness.id == user_id).first()
        
        if not consumer and not business:
            print(f"❌ No user found with ID {user_id}")
            return
        
        user_type = "consumer" if consumer else "business"
        user = consumer if consumer else business
        
        print("\n" + "=" * 80)
        print(f"USER DETAILS - ID {user_id}")
        print("=" * 80)
        print(f"Type: {user_type.upper()}")
        print(f"Email: {user.email}")
        if consumer:
            print(f"Name: {user.name}")
        else:
            print(f"Business: {user.business_name}")
        
        # Get transactions
        if consumer:
            transactions = db.query(Transaction).filter(
                Transaction.user_consumer_id == user_id
            ).order_by(Transaction.date.desc()).limit(20).all()
        else:
            transactions = db.query(Transaction).filter(
                Transaction.user_business_id == user_id
            ).order_by(Transaction.date.desc()).limit(20).all()
        
        print(f"\nTotal Transactions: {len(transactions)}")
        
        if transactions:
            print("\n" + "=" * 80)
            print("RECENT TRANSACTIONS (Latest 20)")
            print("=" * 80)
            
            for t in transactions:
                print(f"\nID: {t.id}")
                print(f"  Date: {t.date}")
                print(f"  Merchant: {t.merchant_name_raw}")
                print(f"  Amount: ₹{t.amount}")
                print(f"  Category: {t.category}")
                print(f"  Source: {t.source_type}")
                print(f"  Payment: {t.payment_channel}")
                
                # Show Gmail-specific info
                if t.source_type.value == 'GMAIL':
                    parsed = t.parsed_fields or {}
                    print(f"  📧 Email Subject: {parsed.get('email_subject', 'N/A')}")
                    print(f"  📤 Sender: {parsed.get('sender', 'N/A')}")
                    print(f"  🔄 Auto-ingested: {parsed.get('auto_ingested', False)}")
                    print(f"  📨 Monitored Email: {parsed.get('monitored_email', 'N/A')}")
        else:
            print("\n⚠️  No transactions found for this user")
            print("\nTo add Gmail transactions:")
            print(f"1. Authenticate: POST http://localhost:8000/api/v1/n8n/gmail/authenticate")
            print(f"2. Start monitor: POST http://localhost:8000/api/v1/n8n/gmail/start")
            print(f"   (Login as User ID {user_id} to get Bearer token)")
            print(f"3. Check manually: POST http://localhost:8000/api/v1/n8n/gmail/check-now")
        
        print("\n" + "=" * 80)
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Test user transactions and Gmail monitor')
    parser.add_argument('--list-users', action='store_true', help='List all users')
    parser.add_argument('--user-id', type=int, help='Show transactions for specific user ID')
    
    args = parser.parse_args()
    
    if args.list_users:
        list_users()
    elif args.user_id:
        show_user_transactions(args.user_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
