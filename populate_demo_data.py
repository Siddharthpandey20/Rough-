"""
Enhanced Demo Data Generator - Populates database directly
Creates realistic transactions with proper relationships
"""

import sys
import random
from datetime import datetime, timedelta

print("=" * 60)
print("LUMEN Enhanced Demo Data Generator")
print("=" * 60)

try:
    from faker import Faker
except ImportError:
    print("\n❌ Faker not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "faker"])
    from faker import Faker

# Initialize
fake = Faker('en_IN')  # Indian locale

# Import app components
from app.core.database import SessionLocal
from app.models.user import UserConsumer, UserBusiness
from app.models.transaction import Transaction, PaymentChannel, SourceType as TransactionSourceType
from app.models.merchant import Merchant
from app.models.source import Source
from app.utils.auth import get_password_hash

# Configuration
NUM_TRANSACTIONS_CONSUMER = 100
NUM_TRANSACTIONS_BUSINESS = 50
ANOMALY_RATE = 0.05  # 5% anomalies

# Consumer categories and merchants
CONSUMER_CATEGORIES = {
    "Groceries": ["BigBasket", "DMart", "Reliance Fresh", "More", "Spencer's", "Local Kirana"],
    "Food & Dining": ["Swiggy", "Zomato", "McDonald's", "Domino's", "KFC", "Cafe Coffee Day", "Starbucks"],
    "Transport": ["Uber", "Ola", "Rapido", "Indian Oil", "HP Petrol", "BMTC", "Metro"],
    "Utilities": ["Bescom", "BSNL", "Airtel", "Jio", "Tata Sky", "ACT Fibernet"],
    "Entertainment": ["BookMyShow", "Netflix", "Amazon Prime", "Spotify", "PVR Cinemas"],
    "Shopping": ["Amazon India", "Flipkart", "Myntra", "Decathlon", "Lifestyle", "Westside"],
    "Healthcare": ["Apollo Pharmacy", "Medlife", "1mg", "Practo", "Fortis Hospital"],
    "Education": ["Udemy", "Coursera", "Byju's", "Unacademy", "Khan Academy"]
}

# Business categories and merchants
BUSINESS_CATEGORIES = {
    "Inventory": ["ABC Distributors", "XYZ Wholesalers", "National Suppliers", "Metro Cash & Carry"],
    "Supplies": ["Office Depot", "D-Mart Wholesale", "Staples", "Amazon Business"],
    "Services": ["CA Sharma & Associates", "Legal Services Ltd", "IT Solutions Co"],
    "Salary": ["Employee Payroll", "Staff Payments", "Contractor Payments"],
    "Utilities": ["Bescom Business", "Airtel Corporate", "BSNL Enterprise"],
    "Travel": ["MakeMyTrip Business", "Goibibo Corporate", "Uber for Business"],
    "Marketing": ["Google Ads", "Facebook Ads", "LinkedIn Premium", "Print Media Co"]
}

def create_demo_users(db):
    """Create demo consumer and business users"""
    print("\n1. Creating demo users...")
    
    # Consumer user
    consumer = db.query(UserConsumer).filter(UserConsumer.email == "demo.consumer@lumen.app").first()
    if not consumer:
        consumer = UserConsumer(
            name="Demo Consumer",
            email="demo.consumer@lumen.app",
            phone="+919876543210",
            hashed_password=get_password_hash("Demo@123"),
            timezone="Asia/Kolkata",
            currency="INR",
            consent_gmail_ingest=True,
            consent_whatsapp_ingest=True,
            is_active=True
        )
        db.add(consumer)
        db.flush()
        print(f"   ✅ Created consumer user: {consumer.email}")
    else:
        print(f"   ✅ Consumer user exists: {consumer.email}")
    
    # Business user
    business = db.query(UserBusiness).filter(UserBusiness.email == "demo.business@lumen.app").first()
    if not business:
        business = UserBusiness(
            business_name="Demo Enterprises Pvt Ltd",
            contact_person="Demo Business Owner",
            email="demo.business@lumen.app",
            phone="+919876543211",
            hashed_password=get_password_hash("Demo@123"),
            gstin="29ABCDE1234F1Z5",
            business_type="Retail",
            timezone="Asia/Kolkata",
            currency="INR",
            is_active=True
        )
        db.add(business)
        db.flush()
        print(f"   ✅ Created business user: {business.email}")
    else:
        print(f"   ✅ Business user exists: {business.email}")
    
    db.commit()
    return consumer, business

def create_merchants(db, user_id, user_type, categories):
    """Create merchant records"""
    merchants = []
    
    for category, merchant_names in categories.items():
        for name in merchant_names:
            merchant = Merchant(
                user_consumer_id=user_id if user_type == "consumer" else None,
                user_business_id=user_id if user_type == "business" else None,
                name_normalized=name.lower(),
                name_variants=[name, name.upper(), name.replace(" ", "")]
            )
            db.add(merchant)
            merchants.append(merchant)
    
    db.flush()
    return merchants

def generate_transaction_amount(category, is_anomaly=False):
    """Generate realistic transaction amounts"""
    # Normal ranges
    ranges = {
        "Groceries": (200, 3000),
        "Food & Dining": (150, 1500),
        "Transport": (50, 500),
        "Utilities": (500, 5000),
        "Entertainment": (100, 1000),
        "Shopping": (500, 10000),
        "Healthcare": (300, 5000),
        "Education": (500, 15000),
        "Inventory": (10000, 500000),
        "Supplies": (5000, 50000),
        "Services": (10000, 100000),
        "Salary": (15000, 50000),
        "Utilities": (5000, 20000),
        "Travel": (5000, 30000),
        "Marketing": (5000, 100000)
    }
    
    min_amt, max_amt = ranges.get(category, (100, 1000))
    
    if is_anomaly:
        # Make it 3-5x the normal range
        factor = random.uniform(3, 5)
        return round(random.uniform(min_amt * factor, max_amt * factor), 2)
    else:
        return round(random.uniform(min_amt, max_amt), 2)

def create_transactions(db, user, user_type, categories, num_transactions):
    """Create realistic transactions"""
    print(f"\n2. Creating {num_transactions} transactions for {user_type}...")
    
    # Create merchants first
    merchants = create_merchants(db, user.id, user_type, categories)
    db.flush()
    
    # Get merchant map
    merchant_map = {}
    for category, names in categories.items():
        merchant_map[category] = [m for m in merchants if m.name_normalized in [n.lower() for n in names]]
    
    # Payment channels distribution
    payment_channels = [
        PaymentChannel.UPI, PaymentChannel.UPI, PaymentChannel.UPI,  # UPI is most common
        PaymentChannel.CARD, PaymentChannel.CARD,
        PaymentChannel.CASH,
        PaymentChannel.NETBANKING,
        PaymentChannel.WALLET
    ]
    
    source_types = [
        TransactionSourceType.GMAIL,
        TransactionSourceType.UPLOAD,
        TransactionSourceType.WHATSAPP,
        TransactionSourceType.MANUAL
    ]
    
    transactions = []
    anomaly_count = 0
    
    for i in range(num_transactions):
        # Random date in last 90 days
        days_ago = random.randint(0, 90)
        transaction_date = datetime.utcnow() - timedelta(days=days_ago)
        
        # Select category and merchant
        category = random.choice(list(categories.keys()))
        merchant = random.choice(merchant_map[category])
        
        # Determine if anomaly
        is_anomaly = random.random() < ANOMALY_RATE
        if is_anomaly:
            anomaly_count += 1
        
        # Generate amount
        amount = generate_transaction_amount(category, is_anomaly)
        
        # Create source
        source = Source(
            user_consumer_id=user.id if user_type == "consumer" else None,
            user_business_id=user.id if user_type == "business" else None,
            source_type=random.choice(source_types),
            processed=True,
            processed_at=transaction_date,
            received_at=transaction_date
        )
        db.add(source)
        db.flush()
        
        # Create transaction
        transaction = Transaction(
            user_consumer_id=user.id if user_type == "consumer" else None,
            user_business_id=user.id if user_type == "business" else None,
            user_type="CONSUMER" if user_type == "consumer" else "BUSINESS",
            source_id=source.id,
            merchant_id=merchant.id,
            amount=amount,
            currency="INR",
            date=transaction_date,
            merchant_name_raw=merchant.name_variants[0],
            category=category,
            payment_channel=random.choice(payment_channels),
            source_type=source.source_type,
            invoice_no=f"INV{fake.random_number(digits=8)}" if random.random() > 0.3 else None,
            flagged=is_anomaly,
            confirmed=not is_anomaly,  # Normal transactions are auto-confirmed
            classification_confidence=random.uniform(0.7, 0.99) if not is_anomaly else random.uniform(0.4, 0.7),
            anomaly_score=random.uniform(0.7, 0.95) if is_anomaly else random.uniform(0.1, 0.3),
            parsed_fields={
                "demo_data": True,
                "anomaly": is_anomaly,
                "description": fake.sentence() if random.random() > 0.5 else None
            }
        )
        db.add(transaction)
        transactions.append(transaction)
        
        if (i + 1) % 20 == 0:
            print(f"   Progress: {i + 1}/{num_transactions} transactions created")
    
    db.commit()
    print(f"   ✅ Created {len(transactions)} transactions ({anomaly_count} anomalies)")
    return transactions

def main():
    """Generate all demo data"""
    try:
        db = SessionLocal()
        
        # Create users
        consumer, business = create_demo_users(db)
        
        # Create consumer transactions
        consumer_txns = create_transactions(
            db, consumer, "consumer", 
            CONSUMER_CATEGORIES, NUM_TRANSACTIONS_CONSUMER
        )
        
        # Create business transactions
        business_txns = create_transactions(
            db, business, "business",
            BUSINESS_CATEGORIES, NUM_TRANSACTIONS_BUSINESS
        )
        
        # Summary
        print("\n" + "=" * 60)
        print("Demo Data Generation Complete!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"   Consumer Transactions: {len(consumer_txns)}")
        print(f"   Business Transactions: {len(business_txns)}")
        print(f"   Total: {len(consumer_txns) + len(business_txns)}")
        
        print(f"\n👤 Demo Users Created:")
        print(f"   Consumer: demo.consumer@lumen.app / Demo@123")
        print(f"   Business: demo.business@lumen.app / Demo@123")
        
        print(f"\n🔍 Test the features:")
        print(f"   1. Login with demo users")
        print(f"   2. View transactions: GET /api/v1/transactions")
        print(f"   3. Check stats: GET /api/v1/transactions/stats")
        print(f"   4. View anomalies: GET /api/v1/transactions?flagged_only=true")
        print(f"   5. Test chat: POST /api/v1/chat/message")
        print(f"   6. Confirm transactions: POST /api/v1/transactions/{{id}}/confirm")
        
        print(f"\n📖 Access API docs: http://localhost:8000/api/docs")
        print("=" * 60)
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
