"""
Debug script to see what emails are in Gmail and why they're not creating transactions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gmail_monitor_service import gmail_monitor
from app.core.config import settings
import pickle

def check_recent_emails():
    """Check what emails are in the Gmail inbox"""
    
    print("\n" + "=" * 80)
    print("GMAIL INBOX ANALYSIS")
    print("=" * 80)
    
    # Load Gmail credentials
    token_path = f"{settings.GMAIL_TOKEN_PATH}_1"
    
    if not os.path.exists(token_path):
        print(f"❌ No Gmail token found at {token_path}")
        print("Run: POST /api/v1/n8n/gmail/authenticate first")
        return
    
    with open(token_path, 'rb') as token:
        creds = pickle.load(token)
    
    from googleapiclient.discovery import build
    service = build('gmail', 'v1', credentials=creds)
    
    print(f"\n📧 Checking inbox for: {gmail_monitor.gmail_service._get_authenticated_email() if hasattr(gmail_monitor.gmail_service, '_get_authenticated_email') else 'siddharth24102@iiitnr.edu.in'}")
    
    # Get profile
    try:
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ Authenticated as: {profile.get('emailAddress')}")
    except Exception as e:
        print(f"⚠️  Could not get profile: {e}")
    
    # Check for unread transaction emails
    query = 'is:unread (payment OR transaction OR receipt OR invoice OR UPI OR IMPS OR NEFT OR debited OR credited OR "payment confirmation" OR bank OR "Rs." OR "INR" OR "₹")'
    
    print(f"\n🔍 Searching with query: {query}")
    
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        
        print(f"\n📊 Found {len(messages)} UNREAD potential transaction emails")
        
        if len(messages) == 0:
            print("\n⚠️  No unread transaction emails found!")
            print("Possible reasons:")
            print("1. All emails have been marked as read (processed)")
            print("2. No transaction emails in inbox")
            print("3. Search query doesn't match email content")
            
            # Check all recent emails (read + unread)
            print("\n🔍 Checking recent emails (last 7 days, including read)...")
            from datetime import datetime, timedelta
            after_date = (datetime.utcnow() - timedelta(days=7)).strftime('%Y/%m/%d')
            all_query = f'after:{after_date} (payment OR transaction OR Rs OR ₹ OR INR)'
            
            all_results = service.users().messages().list(
                userId='me',
                q=all_query,
                maxResults=10
            ).execute()
            
            all_messages = all_results.get('messages', [])
            print(f"📊 Found {len(all_messages)} total emails (read + unread) in last 7 days")
            
            if len(all_messages) > 0:
                print("\n📧 Recent emails:")
                for i, msg in enumerate(all_messages[:5], 1):
                    try:
                        message = service.users().messages().get(
                            userId='me',
                            id=msg['id'],
                            format='metadata',
                            metadataHeaders=['Subject', 'From', 'Date']
                        ).execute()
                        
                        headers = {h['name']: h['value'] for h in message['payload']['headers']}
                        subject = headers.get('Subject', 'No subject')
                        sender = headers.get('From', 'Unknown')
                        date = headers.get('Date', 'Unknown')
                        labels = message.get('labelIds', [])
                        is_unread = 'UNREAD' in labels
                        
                        print(f"\n{i}. Message ID: {msg['id']}")
                        print(f"   Subject: {subject[:100]}")
                        print(f"   From: {sender[:100]}")
                        print(f"   Date: {date}")
                        print(f"   Status: {'UNREAD' if is_unread else 'READ'}")
                    except Exception as e:
                        print(f"\n{i}. Error reading message {msg['id']}: {e}")
            
            return
        
        # Show details of unread emails
        print("\n" + "=" * 80)
        print("UNREAD TRANSACTION EMAILS")
        print("=" * 80)
        
        for i, msg in enumerate(messages, 1):
            print(f"\n{i}. MESSAGE ID: {msg['id']}")
            print("-" * 80)
            
            try:
                # Get full message
                message = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                headers = {h['name']: h['value'] for h in message['payload']['headers']}
                subject = headers.get('Subject', 'No subject')
                sender = headers.get('From', 'Unknown')
                date = headers.get('Date', 'Unknown')
                
                print(f"Subject: {subject}")
                print(f"From: {sender}")
                print(f"Date: {date}")
                
                # Get body preview
                import base64
                body = ""
                if 'parts' in message['payload']:
                    for part in message['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            data = part['body'].get('data', '')
                            if data:
                                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                                break
                else:
                    data = message['payload']['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                
                print(f"\nBody Preview (first 500 chars):")
                print(body[:500])
                
                # Check if it looks like a transaction
                text_lower = (subject + " " + body).lower()
                has_amount = any(keyword in text_lower for keyword in ['rs.', 'rs ', 'inr', '₹'])
                has_transaction_word = any(keyword in text_lower for keyword in ['payment', 'transaction', 'debited', 'credited', 'paid'])
                
                print(f"\n🔍 Analysis:")
                print(f"   Has amount indicator: {has_amount}")
                print(f"   Has transaction word: {has_transaction_word}")
                print(f"   Looks like transaction: {has_amount and has_transaction_word}")
                
            except Exception as e:
                print(f"Error reading message: {e}")
        
        print("\n" + "=" * 80)
        print("PROCESSED MESSAGE IDs (already handled)")
        print("=" * 80)
        if len(gmail_monitor.processed_message_ids) > 0:
            for msg_id in list(gmail_monitor.processed_message_ids)[:10]:
                print(f"  - {msg_id}")
            if len(gmail_monitor.processed_message_ids) > 10:
                print(f"  ... and {len(gmail_monitor.processed_message_ids) - 10} more")
        else:
            print("  (none)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_recent_emails()
