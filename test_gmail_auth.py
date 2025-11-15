"""
Gmail Authentication Test Script
Run this to authenticate Gmail before starting the main server
"""

import os
import pickle
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Configuration
GMAIL_CREDENTIALS_PATH = "credentials/gmail_credentials.json"
GMAIL_TOKEN_PATH = "credentials/gmail_token.json_1"
USER_EMAIL = "siddharth24102@iiitnr.edu.in"


def authenticate_gmail():
    """Authenticate with Gmail and save token"""
    try:
        logger.info("=" * 60)
        logger.info("Gmail Authentication Setup")
        logger.info("=" * 60)
        
        # Check if credentials file exists
        if not os.path.exists(GMAIL_CREDENTIALS_PATH):
            logger.error(f"❌ Gmail credentials file not found: {GMAIL_CREDENTIALS_PATH}")
            logger.error("📝 Please ensure gmail_credentials.json exists in credentials/ folder")
            logger.error("💡 Get it from Google Cloud Console: https://console.cloud.google.com/apis/credentials")
            return False
        
        logger.info(f"✅ Found credentials file: {GMAIL_CREDENTIALS_PATH}")
        
        creds = None
        
        # Load existing token if available
        if os.path.exists(GMAIL_TOKEN_PATH):
            logger.info(f"📂 Loading existing token from {GMAIL_TOKEN_PATH}")
            with open(GMAIL_TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("🔄 Refreshing expired token...")
                try:
                    creds.refresh(Request())
                    logger.info("✅ Token refreshed successfully!")
                except Exception as e:
                    logger.error(f"❌ Token refresh failed: {e}")
                    logger.info("🔄 Starting new OAuth flow...")
                    creds = None
            
            if not creds:
                logger.info("🔐 Starting OAuth 2.0 authentication flow...")
                logger.info(f"📧 Authenticating as: {USER_EMAIL}")
                logger.info("🌐 A browser window will open - please:")
                logger.info("   1. Select your Google account")
                logger.info("   2. Grant Gmail read-only access")
                logger.info("   3. Complete the authorization")
                logger.info("")
                logger.info("⚠️ IMPORTANT: If you get 'redirect_uri_mismatch' error:")
                logger.info("   1. Go to https://console.cloud.google.com/apis/credentials")
                logger.info("   2. Click on your OAuth 2.0 Client ID")
                logger.info("   3. Add these Authorized redirect URIs:")
                logger.info("      - http://localhost:8080/")
                logger.info("      - http://localhost:8090/")
                logger.info("      - http://localhost/")
                logger.info("   4. Save and try again")
                logger.info("")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    GMAIL_CREDENTIALS_PATH, SCOPES
                )
                
                # Try multiple ports to avoid conflicts
                ports_to_try = [8080, 8090, 0]
                auth_success = False
                last_error = None
                
                for port in ports_to_try:
                    try:
                        logger.info(f"🔄 Attempting OAuth on port {port if port != 0 else 'auto'}...")
                        creds = flow.run_local_server(
                            port=port,
                            success_message='✅ Authentication successful! You can close this window.',
                            open_browser=True
                        )
                        auth_success = True
                        logger.info(f"✅ OAuth successful on port {port if port != 0 else 'auto'}!")
                        break
                    except Exception as port_error:
                        last_error = port_error
                        if 'redirect_uri_mismatch' in str(port_error).lower():
                            logger.warning(f"❌ Port {port} failed: redirect_uri_mismatch")
                            continue
                        else:
                            raise port_error
                
                if not auth_success:
                    raise last_error if last_error else Exception("All OAuth attempts failed")
                
                logger.info("✅ OAuth flow completed successfully!")
            
            # Save credentials
            logger.info(f"💾 Saving token to {GMAIL_TOKEN_PATH}")
            with open(GMAIL_TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)
            logger.info("✅ Token saved successfully!")
        else:
            logger.info("✅ Valid token already exists!")
        
        # Test the connection
        logger.info("\n📧 Testing Gmail connection...")
        service = build('gmail', 'v1', credentials=creds)
        
        # Get profile info
        profile = service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress')
        total_messages = profile.get('messagesTotal', 0)
        
        logger.info(f"✅ Connected to Gmail successfully!")
        logger.info(f"📧 Email: {email}")
        logger.info(f"📊 Total messages: {total_messages}")

        # Ensure authenticated account is the expected monitored account
        if email and email.lower() != USER_EMAIL.lower():
            logger.error(f"🔐 Authenticated account mismatch: expected {USER_EMAIL}, got {email}")
            # Remove token so user can re-authenticate
            try:
                if os.path.exists(GMAIL_TOKEN_PATH):
                    os.remove(GMAIL_TOKEN_PATH)
                    logger.info(f"🗑️ Removed token at {GMAIL_TOKEN_PATH} due to account mismatch")
            except Exception as rm_err:
                logger.warning(f"Could not remove token file: {rm_err}")

            logger.error("Please re-run the authentication and select the correct Gmail account")
            return False
        
        # Check for unread transaction emails
        logger.info("\n🔍 Checking for unread transaction emails...")
        query = 'is:unread (payment OR transaction OR receipt OR invoice OR UPI OR IMPS OR NEFT OR debited OR credited OR bank)'
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        unread_count = len(messages)
        
        logger.info(f"📬 Found {unread_count} unread transaction-related emails")
        
        if unread_count > 0:
            logger.info("✅ Ready to process transaction emails!")
        else:
            logger.info("ℹ️ No unread transaction emails found")
            logger.info("💡 Send a test payment email to see it in action")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Gmail Authentication Complete!")
        logger.info("=" * 60)
        logger.info("\n📝 Next steps:")
        logger.info("   1. Start the main server: python main.py")
        logger.info("   2. Gmail monitor will start automatically")
        logger.info("   3. Send transaction emails and watch them get processed!")
        logger.info("\n💡 Useful endpoints:")
        logger.info("   - GET  /api/v1/n8n/gmail/status - Check monitoring status")
        logger.info("   - POST /api/v1/n8n/gmail/check-now - Force immediate check")
        logger.info("   - POST /api/v1/n8n/gmail/start - Start monitoring")
        logger.info("   - POST /api/v1/n8n/gmail/stop - Stop monitoring")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Authentication failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = authenticate_gmail()
    exit(0 if success else 1)
