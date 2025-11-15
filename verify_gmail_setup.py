"""
Quick verification script to check Gmail monitor setup

Run this before starting the main application to verify everything is configured correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.user import UserConsumer, UserBusiness
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_gmail_credentials():
    """Check if Gmail credentials file exists"""
    if os.path.exists(settings.GMAIL_CREDENTIALS_PATH):
        logger.info(f"✅ Gmail credentials found: {settings.GMAIL_CREDENTIALS_PATH}")
        return True
    else:
        logger.error(f"❌ Gmail credentials NOT found: {settings.GMAIL_CREDENTIALS_PATH}")
        logger.error("   Please download OAuth credentials from Google Cloud Console")
        logger.error("   and save as credentials/gmail_credentials.json")
        return False


def check_gmail_token():
    """Check if Gmail token exists"""
    token_path = f"{settings.GMAIL_TOKEN_PATH}_1"
    if os.path.exists(token_path):
        logger.info(f"✅ Gmail token found: {token_path}")
        logger.info("   (Already authenticated - no need to authenticate again)")
        return True
    else:
        logger.warning(f"⚠️  Gmail token NOT found: {token_path}")
        logger.warning("   You will need to authenticate on first run")
        logger.warning("   Call: POST /api/v1/n8n/gmail/authenticate")
        return False


def check_database():
    """Check database connection and users"""
    try:
        db = SessionLocal()
        
        # Count users
        consumer_count = db.query(UserConsumer).count()
        business_count = db.query(UserBusiness).count()
        
        logger.info(f"✅ Database connected")
        logger.info(f"   Consumer users: {consumer_count}")
        logger.info(f"   Business users: {business_count}")
        
        if consumer_count > 0:
            logger.info("\n📋 Sample Consumer Users:")
            for user in db.query(UserConsumer).limit(3).all():
                logger.info(f"   - ID {user.id}: {user.email} ({user.name})")
        
        if business_count > 0:
            logger.info("\n📋 Sample Business Users:")
            for user in db.query(UserBusiness).limit(3).all():
                logger.info(f"   - ID {user.id}: {user.email} ({user.business_name})")
        
        db.close()
        return True
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return False


def main():
    print("\n" + "=" * 80)
    print("GMAIL MONITOR - PRE-FLIGHT CHECK")
    print("=" * 80 + "\n")
    
    checks = []
    
    # Check 1: Gmail credentials
    checks.append(("Gmail Credentials", check_gmail_credentials()))
    
    # Check 2: Gmail token
    checks.append(("Gmail Token", check_gmail_token()))
    
    # Check 3: Database
    checks.append(("Database", check_database()))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_passed = all(result for _, result in checks)
    
    for name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
    
    print("\n" + "=" * 80)
    
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\n📝 Next steps:")
        print("1. Start the application: python main.py")
        print("2. Login as a user to get Bearer token")
        print("3. Start Gmail monitor: POST /api/v1/n8n/gmail/start (with token)")
        print("4. Check status: GET /api/v1/n8n/gmail/status")
        print("\n📖 Full guide: See GMAIL_MONITOR_GUIDE.md")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\n🔧 Fix the issues above before starting the application")
        print("📖 See GMAIL_MONITOR_GUIDE.md for help")
    
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
