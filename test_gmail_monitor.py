"""
Test script to verify Gmail monitor service
Run this to check if the monitor can initialize properly
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_import():
    """Test if all imports work"""
    print("Testing imports...")
    
    try:
        from app.services.gmail_monitor_service import gmail_monitor
        print("✅ Successfully imported gmail_monitor")
    except Exception as e:
        print(f"❌ Failed to import gmail_monitor: {e}")
        return False
    
    try:
        from app.services.gmail_service import GmailService
        print("✅ Successfully imported GmailService")
    except Exception as e:
        print(f"❌ Failed to import GmailService: {e}")
        return False
    
    return True


def test_monitor_status():
    """Test monitor status check"""
    print("\nTesting monitor status...")
    
    try:
        from app.services.gmail_monitor_service import gmail_monitor
        print(f"Monitor running: {gmail_monitor.is_running}")
        print(f"Check interval: {gmail_monitor.check_interval}s")
        print(f"Last check: {gmail_monitor.last_check_time}")
        print(f"Processed messages: {len(gmail_monitor.processed_message_ids)}")
        print("✅ Monitor status check successful")
        return True
    except Exception as e:
        print(f"❌ Monitor status check failed: {e}")
        return False


def test_hardcoded_config():
    """Test hardcoded configuration"""
    print("\nTesting hardcoded configuration...")
    
    try:
        from app.services.gmail_monitor_service import MONITORED_USER_EMAIL, MONITORED_USER_ID, MONITORED_USER_TYPE
        print(f"Monitored email: {MONITORED_USER_EMAIL}")
        print(f"User ID: {MONITORED_USER_ID}")
        print(f"User type: {MONITORED_USER_TYPE}")
        
        if MONITORED_USER_EMAIL == "siddharth24102@iiitnr.edu.in":
            print("✅ Hardcoded configuration correct")
            return True
        else:
            print("❌ Email configuration incorrect")
            return False
    except Exception as e:
        print(f"❌ Configuration check failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Gmail Monitor Service Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Import Test", test_import()))
    results.append(("Status Test", test_monitor_status()))
    results.append(("Config Test", test_hardcoded_config()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed! Gmail monitor is ready to use.")
        print("\nNext steps:")
        print("1. Ensure credentials/gmail_credentials.json exists")
        print("2. Run: python main.py")
        print("3. Authenticate Gmail when browser opens")
        print("4. Monitor will start automatically")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("=" * 60)
