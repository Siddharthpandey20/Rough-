"""
Demo Data Generator for Testing and Hackathon Demo
"""

import random
from datetime import datetime, timedelta
from faker import Faker
import requests
import json

fake = Faker('en_IN')  # Indian locale

# Demo configuration
BASE_URL = "http://localhost:8000/api/v1"
NUM_USERS = 5
NUM_TRANSACTIONS_PER_USER = 50

# Categories
CONSUMER_CATEGORIES = ["Groceries", "Food & Dining", "Transport", "Utilities", "Entertainment"]
BUSINESS_CATEGORIES = ["Inventory", "Supplies", "Travel", "Services", "Salary"]

# Merchants by category
MERCHANTS = {
    "Groceries": ["Big Bazaar", "DMart", "Reliance Fresh", "More Supermarket", "Spencer's"],
    "Food & Dining": ["Zomato", "Swiggy", "McDonald's", "Pizza Hut", "Taj Restaurant"],
    "Transport": ["Uber", "Ola", "Indian Railways", "BMTC", "Rapido"],
    "Utilities": ["BESCOM", "BWSSB", "Airtel", "Jio Fiber", "ACT Fibernet"],
    "Entertainment": ["BookMyShow", "Netflix", "Amazon Prime", "Spotify", "YouTube Premium"],
    "Inventory": ["Supplier A", "Supplier B", "Wholesale Market", "Manufacturer X"],
    "Supplies": ["Office Depot", "Stationery World", "Tech Supplies", "Packaging Co"],
    "Travel": ["MakeMyTrip", "Goibibo", "Indian Hotels", "Cab Service"],
    "Services": ["Consultant A", "Marketing Agency", "IT Services", "Legal Firm"],
    "Salary": ["Employee 1", "Employee 2", "Employee 3", "Contractor A"]
}

# Payment channels
PAYMENT_CHANNELS = ["UPI", "Card", "Cash", "BankTransfer", "Wallet"]

# Source types
SOURCE_TYPES = ["Upload", "Gmail", "UPIFeed", "SMS"]


class DemoDataGenerator:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.users = []
    
    def generate_users(self, num_users=NUM_USERS):
        """Generate demo users"""
        print(f"\n📝 Generating {num_users} demo users...")
        
        for i in range(num_users):
            user_type = "consumer" if i < num_users // 2 else "business"
            
            if user_type == "consumer":
                user_data = {
                    "email": f"demo_consumer_{i+1}@lumen.app",
                    "password": "Demo@123",
                    "name": fake.name(),
                    "phone": fake.phone_number(),
                    "user_type": "consumer"
                }
            else:
                user_data = {
                    "email": f"demo_business_{i+1}@lumen.app",
                    "password": "Demo@123",
                    "name": fake.name(),
                    "user_type": "business",
                    "business_name": fake.company(),
                    "contact_person": fake.name(),
                    "gstin": f"22{fake.random_number(digits=13)}"
                }
            
            try:
                response = requests.post(
                    f"{self.base_url}/auth/register",
                    json=user_data
                )
                
                if response.status_code == 201:
                    result = response.json()
                    self.users.append({
                        "user_id": result["user_id"],
                        "user_type": result["user_type"],
                        "token": result["access_token"],
                        "email": user_data["email"]
                    })
                    print(f"  ✓ Created {user_type} user: {user_data['email']}")
                else:
                    print(f"  ✗ Failed to create user: {response.text}")
            
            except Exception as e:
                print(f"  ✗ Error creating user: {e}")
        
        print(f"\n✓ Created {len(self.users)} users")
    
    def generate_transactions(self, num_per_user=NUM_TRANSACTIONS_PER_USER):
        """Generate demo transactions"""
        print(f"\n💰 Generating {num_per_user} transactions per user...")
        
        total_generated = 0
        total_flagged = 0
        
        for user in self.users:
            headers = {"Authorization": f"Bearer {user['token']}"}
            categories = CONSUMER_CATEGORIES if user['user_type'] == 'consumer' else BUSINESS_CATEGORIES
            
            for i in range(num_per_user):
                # Generate transaction data
                category = random.choice(categories)
                merchant = random.choice(MERCHANTS[category])
                
                # Base amount for category (with variation)
                base_amounts = {
                    "Groceries": 1500, "Food & Dining": 500, "Transport": 200,
                    "Utilities": 1000, "Entertainment": 300, "Inventory": 50000,
                    "Supplies": 5000, "Travel": 8000, "Services": 15000, "Salary": 30000
                }
                
                base = base_amounts[category]
                amount = base * random.uniform(0.5, 2.0)
                
                # Add occasional anomalies (10% chance)
                is_anomaly = random.random() < 0.1
                if is_anomaly:
                    amount *= random.uniform(3.0, 8.0)  # 3-8x normal amount
                    total_flagged += 1
                
                # Random date in last 90 days
                days_ago = random.randint(0, 90)
                date = datetime.now() - timedelta(days=days_ago)
                
                transaction_data = {
                    "amount": round(amount, 2),
                    "currency": "INR",
                    "date": date.isoformat(),
                    "merchant_name_raw": merchant,
                    "invoice_no": f"INV-{fake.random_number(digits=8)}",
                    "payment_channel": random.choice(PAYMENT_CHANNELS),
                    "source_type": random.choice(SOURCE_TYPES),
                    "category": category,
                    "user_type": user['user_type'],
                    "source_id": 1,  # Placeholder
                    "ocr_confidence": random.uniform(0.8, 0.99)
                }
                
                # Note: In real implementation, you'd call the transaction creation endpoint
                # For demo, we're showing the structure
                total_generated += 1
            
            print(f"  ✓ Generated {num_per_user} transactions for {user['email']}")
        
        print(f"\n✓ Generated {total_generated} transactions")
        print(f"  🚨 {total_flagged} anomalies created for demo")
    
    def generate_chat_scenarios(self):
        """Generate sample chat interactions"""
        print("\n💬 Generating chat scenarios...")
        
        chat_queries = [
            "How much did I spend on groceries this month?",
            "What was my biggest expense last week?",
            "Show me all transactions above ₹5000",
            "Did I pay ₹1500 to Big Bazaar on {date}?",
            "Where do I spend the most money?",
            "What's unusual about my spending this month?",
            "List all flagged transactions",
            "What are my recent UPI payments?"
        ]
        
        for user in self.users[:2]:  # Test with first 2 users
            headers = {"Authorization": f"Bearer {user['token']}"}
            
            for query in random.sample(chat_queries, 3):
                # Replace {date} placeholder
                if "{date}" in query:
                    date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
                    query = query.replace("{date}", date)
                
                try:
                    response = requests.post(
                        f"{self.base_url}/chat/message",
                        headers=headers,
                        json={"message": query}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"  ✓ Query: {query[:50]}...")
                        print(f"    Response: {result.get('response', '')[:100]}...")
                    else:
                        print(f"  ✗ Query failed: {query[:50]}...")
                
                except Exception as e:
                    print(f"  ✗ Error: {e}")
        
        print("\n✓ Chat scenarios completed")
    
    def print_summary(self):
        """Print summary of generated data"""
        print("\n" + "="*60)
        print("📊 Demo Data Summary")
        print("="*60)
        print(f"Total Users: {len(self.users)}")
        print(f"Consumer Users: {sum(1 for u in self.users if u['user_type'] == 'consumer')}")
        print(f"Business Users: {sum(1 for u in self.users if u['user_type'] == 'business')}")
        print(f"\nSample Credentials:")
        for user in self.users[:3]:
            print(f"  Email: {user['email']}")
            print(f"  Password: Demo@123")
            print(f"  Token: {user['token'][:50]}...")
            print()
        
        print("\n🎯 Demo Highlights:")
        print("  - Realistic transaction data with amounts based on categories")
        print("  - ~10% anomalous transactions for testing flagging system")
        print("  - Multiple payment channels and sources")
        print("  - 90-day transaction history")
        print("  - Sample chat interactions")
        
        print("\n📖 Next Steps:")
        print("  1. Use demo credentials to login")
        print("  2. Test API endpoints with generated data")
        print("  3. Review flagged transactions")
        print("  4. Try chat queries")
        print("  5. Check anomaly explanations")
        
        print("\n✨ Demo data generation complete!")


def main():
    print("="*60)
    print("🎭 LUMEN Demo Data Generator")
    print("="*60)
    
    generator = DemoDataGenerator()
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/../health")
        if response.status_code != 200:
            print("❌ Server is not responding. Please start the server first:")
            print("   python main.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the server first:")
        print("   python main.py")
        return
    
    print("✓ Server is running\n")
    
    # Generate demo data
    generator.generate_users(num_users=NUM_USERS)
    generator.generate_transactions(num_per_user=NUM_TRANSACTIONS_PER_USER)
    # generator.generate_chat_scenarios()  # Uncomment when chat endpoint is ready
    
    # Print summary
    generator.print_summary()


if __name__ == "__main__":
    # Note: Install faker first: pip install faker
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo data generation interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Server is running (python main.py)")
        print("  2. Database is configured")
        print("  3. All dependencies are installed")
