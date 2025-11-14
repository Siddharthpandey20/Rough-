"""
Test script to verify all features are working
Run this after starting the server
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_health():
    """Test health endpoint"""
    print_section("Testing Health Check")
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_registration():
    """Test user registration"""
    print_section("Testing User Registration")
    try:
        # Consumer registration
        consumer_data = {
            "name": "Test User",
            "email": f"testuser_{datetime.now().timestamp()}@example.com",
            "phone": "+919876543210",
            "password": "TestPass123!",
            "timezone": "Asia/Kolkata",
            "currency": "INR"
        }
        
        response = requests.post(f"{BASE_URL}/auth/register/consumer", json=consumer_data)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200 and "access_token" in result:
            print("✅ Registration successful!")
            return result["access_token"]
        else:
            print("❌ Registration failed")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_gmail_status(token):
    """Test Gmail status endpoint"""
    print_section("Testing Gmail Status")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/ingestion/gmail/status", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_chat_session(token):
    """Test chat session creation"""
    print_section("Testing Chat Session")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/chat/session", headers=headers)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200 and "session_id" in result:
            print("✅ Chat session created!")
            return result["session_id"]
        else:
            print("❌ Session creation failed")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_chat_message(token, session_id):
    """Test sending chat message"""
    print_section("Testing Chat Message")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "message": "Hello! How much did I spend this month?",
            "session_id": session_id
        }
        response = requests.post(f"{BASE_URL}/chat/message", headers=headers, json=data)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200:
            print("✅ Chat response received!")
            return True
        else:
            print("❌ Chat failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_manual_transaction(token):
    """Test manual transaction creation"""
    print_section("Testing Manual Transaction")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "amount": 150.50,
            "paid_to": "Local Grocery Store",
            "purpose": "Weekly groceries",
            "date": datetime.now().isoformat(),
            "payment_method": "cash",
            "category": "Groceries"
        }
        response = requests.post(f"{BASE_URL}/ingestion/manual/consumer", headers=headers, json=data)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200:
            print("✅ Transaction created!")
            return True
        else:
            print("❌ Transaction creation failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n🚀 LUMEN Feature Testing Script")
    print("="*60)
    print("Make sure the server is running: python main.py")
    print("="*60)
    
    results = {
        "health": False,
        "registration": False,
        "gmail_status": False,
        "chat_session": False,
        "chat_message": False,
        "manual_transaction": False
    }
    
    # Test 1: Health check
    results["health"] = test_health()
    if not results["health"]:
        print("\n❌ Server is not running or not responding!")
        print("Please start the server with: python main.py")
        return
    
    # Test 2: Registration
    token = test_registration()
    if not token:
        print("\n❌ Registration failed! Cannot proceed with authenticated tests.")
        return
    results["registration"] = True
    
    # Test 3: Gmail status
    results["gmail_status"] = test_gmail_status(token)
    
    # Test 4: Chat session
    session_id = test_chat_session(token)
    if session_id:
        results["chat_session"] = True
        
        # Test 5: Chat message
        results["chat_message"] = test_chat_message(token, session_id)
    
    # Test 6: Manual transaction
    results["manual_transaction"] = test_manual_transaction(token)
    
    # Print summary
    print_section("Test Summary")
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.ljust(20)}: {status}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! All features are working correctly!")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Check the errors above.")
    
    print("\n📚 Next steps:")
    print("  1. Test Gmail integration (requires setup)")
    print("  2. Test WhatsApp webhook (requires Twilio setup)")
    print("  3. Test OCR with receipt upload")
    print("  4. Check API docs: http://localhost:8000/api/docs")

if __name__ == "__main__":
    main()
