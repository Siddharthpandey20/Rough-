"""
Manual Gmail Authentication for Web Credentials
This script handles OAuth for web-type credentials
"""

import os
import pickle
import logging
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import webbrowser

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
REDIRECT_URI = "http://localhost:8080/"


def manual_authenticate():
    """Manual authentication flow for web credentials"""
    try:
        logger.info("=" * 60)
        logger.info("Gmail Manual Authentication (Web Credentials)")
        logger.info("=" * 60)
        
        # Check if credentials file exists
        if not os.path.exists(GMAIL_CREDENTIALS_PATH):
            logger.error(f"❌ Gmail credentials file not found: {GMAIL_CREDENTIALS_PATH}")
            return False
        
        logger.info(f"✅ Found credentials file: {GMAIL_CREDENTIALS_PATH}")
        
        # Load and check credentials type
        with open(GMAIL_CREDENTIALS_PATH, 'r') as f:
            cred_data = json.load(f)
        
        if 'web' in cred_data:
            logger.info("📝 Detected: WEB application credentials")
            logger.info("🔧 Using manual OAuth flow...")
        elif 'installed' in cred_data:
            logger.info("📝 Detected: DESKTOP application credentials")
            logger.info("💡 You can use the regular test_gmail_auth.py script instead")
        
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
                    creds = None
            
            if not creds:
                logger.info("\n" + "=" * 60)
                logger.info("🔐 Starting Manual OAuth Flow")
                logger.info("=" * 60)
                
                # Create flow with manual redirect URI
                flow = Flow.from_client_secrets_file(
                    GMAIL_CREDENTIALS_PATH,
                    scopes=SCOPES,
                    redirect_uri=REDIRECT_URI
                )
                
                # Generate authorization URL
                auth_url, state = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true',
                    prompt='consent'
                )
                
                logger.info("\n📋 MANUAL STEPS:")
                logger.info("=" * 60)
                logger.info("1. Copy this URL and paste in your browser:")
                logger.info("")
                logger.info(auth_url)
                logger.info("")
                logger.info("2. Sign in with: " + USER_EMAIL)
                logger.info("3. Grant Gmail read-only permission")
                logger.info("4. You'll be redirected to a page that won't load")
                logger.info("5. Copy the ENTIRE URL from browser address bar")
                logger.info("6. Paste it below when prompted")
                logger.info("=" * 60)
                logger.info("")
                
                # Try to open browser automatically
                try:
                    webbrowser.open(auth_url)
                    logger.info("🌐 Browser opened automatically")
                except:
                    logger.info("⚠️ Could not open browser - please open manually")
                
                logger.info("")
                
                # Get authorization response
                redirect_response = input("📥 Paste the full redirect URL here: ").strip()
                
                if not redirect_response:
                    logger.error("❌ No URL provided")
                    return False
                
                # Extract code from redirect URL
                try:
                    flow.fetch_token(authorization_response=redirect_response)
                    creds = flow.credentials
                    logger.info("✅ OAuth flow completed successfully!")
                except Exception as e:
                    logger.error(f"❌ Failed to process redirect URL: {e}")
                    logger.error("\n💡 Make sure you pasted the COMPLETE URL, including:")
                    logger.error("   http://localhost:8080/?code=...")
                    return False
            
            # Save credentials
            logger.info(f"\n💾 Saving token to {GMAIL_TOKEN_PATH}")
            os.makedirs(os.path.dirname(GMAIL_TOKEN_PATH), exist_ok=True)
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
            logger.info("\n📝 Sample emails found:")
            for i, msg in enumerate(messages[:3], 1):
                try:
                    msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
                    headers = {h['name']: h['value'] for h in msg_detail.get('payload', {}).get('headers', [])}
                    subject = headers.get('Subject', 'No subject')
                    logger.info(f"   {i}. {subject[:60]}...")
                except:
                    pass
        else:
            logger.info("ℹ️  No unread transaction emails found")
            logger.info("💡 Send a test payment email to see it in action")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Gmail Authentication Complete!")
        logger.info("=" * 60)
        logger.info("\n📝 Next steps:")
        logger.info("   1. Start the main server: python main.py")
        logger.info("   2. Gmail monitor will start automatically")
        logger.info("   3. Send transaction emails and watch them get processed!")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Authentication failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Gmail Authentication for Web Credentials")
    print("=" * 60)
    print("\nThis script handles OAuth for web-type credentials.")
    print("You'll need to manually copy/paste the redirect URL.")
    print("")
    
    success = manual_authenticate()
    
    if success:
        print("\n✅ SUCCESS! You can now start the server:")
        print("   python main.py")
    else:
        print("\n❌ Authentication failed. Please try again.")
        print("\nAlternatively, you can:")
        print("1. Download DESKTOP credentials from Google Cloud Console")
        print("2. Replace your gmail_credentials.json")
        print("3. Run: python test_gmail_auth.py")
    
    exit(0 if success else 1)
