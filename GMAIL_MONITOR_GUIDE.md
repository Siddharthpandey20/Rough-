# Gmail Transaction Monitor - Complete Guide

## 🎯 Overview

The Gmail monitor checks **siddharth24102@iiitnr.edu.in** for transaction emails and saves ALL found transactions to the currently authenticated user's account.

### Key Concept
- **Monitored Email**: `siddharth24102@iiitnr.edu.in` (fixed, always this one)
- **Transaction Destination**: The user who called `/api/v1/n8n/gmail/start` (dynamic)

## 🚀 Quick Setup

### Step 1: Check Available Users
```bash
python test_user_transactions.py --list-users
```

This shows all users and their transaction counts. Note the User ID you want to use.

### Step 2: Authenticate Gmail (One-time)
```bash
POST http://localhost:8000/api/v1/n8n/gmail/authenticate
```

- Opens browser for OAuth
- Sign in with **siddharth24102@iiitnr.edu.in**
- Saves token to `credentials/gmail_token.json_1`

### Step 3: Login as Your User

Get a Bearer token for the user who should receive transactions:

```bash
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
    "email": "your_email@example.com",
    "password": "your_password"
}
```

Save the `access_token` from the response.

### Step 4: Start Monitor
```bash
POST http://localhost:8000/api/v1/n8n/gmail/start
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**IMPORTANT**: The user whose token you use here will receive ALL transactions!

### Step 5: Force Manual Check (Optional)
```bash
POST http://localhost:8000/api/v1/n8n/gmail/check-now
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Step 6: Verify Transactions
```bash
python test_user_transactions.py --user-id 1
```

Replace `1` with your user ID to see if transactions are appearing.

## 📊 How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                  Gmail: siddharth24102@iiitnr.edu.in            │
│                    (Receives all transaction emails)            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Monitor checks every 30 seconds
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Gmail Monitor Service                      │
│  - Reads emails from siddharth24102@iiitnr.edu.in              │
│  - Extracts transaction details using Gemini AI                │
│  - Saves to: gmail_monitor.current_user_id                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Saves transactions to
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Database - User's Transaction Table                │
│  user_consumer_id = current_user_id (if consumer)              │
│  user_business_id = current_user_id (if business)              │
└─────────────────────────────────────────────────────────────────┘
```

## 🔍 Checking Status

### Via API
```bash
GET http://localhost:8000/api/v1/n8n/gmail/status
```

Response shows:
- `monitored_email`: Which email is being checked
- `transactions_saving_to_user_id`: Which user receives transactions
- `running`: Whether monitor is active
- `last_check`: When last check occurred

### Via Test Script
```bash
python test_user_transactions.py --user-id YOUR_USER_ID
```

Shows recent transactions with Gmail-specific details.

## 🔧 Troubleshooting

### Problem: No transactions appearing

1. **Check monitor is running**:
   ```bash
   GET http://localhost:8000/api/v1/n8n/gmail/status
   ```
   
   Look for `"running": true`

2. **Check which user receives transactions**:
   ```bash
   GET http://localhost:8000/api/v1/n8n/gmail/status
   ```
   
   Look at `transactions_saving_to_user_id` - is this YOUR user ID?

3. **Verify Gmail authentication**:
   ```bash
   ls credentials/gmail_token.json_1
   ```
   
   File should exist. If not, run Step 2 again.

4. **Check for unread emails**:
   - Login to siddharth24102@iiitnr.edu.in
   - Look for unread transaction emails
   - Monitor only processes UNREAD emails

5. **Force manual check**:
   ```bash
   POST http://localhost:8000/api/v1/n8n/gmail/check-now
   Authorization: Bearer YOUR_ACCESS_TOKEN
   ```

### Problem: Transactions going to wrong user

**Solution**: Stop and restart the monitor with the correct user token:

```bash
# Stop monitor
POST http://localhost:8000/api/v1/n8n/gmail/stop
Authorization: Bearer YOUR_ACCESS_TOKEN

# Login as correct user
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
    "email": "correct_user@example.com",
    "password": "password"
}

# Start monitor with correct user
POST http://localhost:8000/api/v1/n8n/gmail/start
Authorization: Bearer NEW_ACCESS_TOKEN
```

### Problem: "Authentication failed" or "Token expired"

**Solution**: Re-authenticate Gmail:

```bash
# Delete old token
rm credentials/gmail_token.json_1

# Re-authenticate
POST http://localhost:8000/api/v1/n8n/gmail/authenticate
```

## 💡 Important Notes

1. **One Monitor, Multiple Users**: Only ONE Gmail monitor can run at a time, but you can change which user receives transactions by restarting the monitor

2. **Unread Only**: Monitor only processes UNREAD emails. Once processed, emails are marked as read to avoid duplicates

3. **30-Second Interval**: Monitor checks every 30 seconds. Manual checks via `/check-now` are instant

4. **Transaction Detection**: Uses Gemini AI to determine if an email is a transaction and extract details

5. **User Type Matters**: The monitor needs to know if the user is "consumer" or "business" for proper categorization

## 📝 Testing Flow

1. **Send test email** to siddharth24102@iiitnr.edu.in with transaction keywords
2. **Check status**: Verify monitor is running
3. **Wait 30 seconds** or trigger manual check
4. **Check transactions**: Use test script to verify

Example test email subject/body:
```
You've paid Rs 299 to Zomato via UPI
Ref: 123456789
```

## 🎓 For Developers

### Key Files
- `app/services/gmail_monitor_service.py`: Main monitor logic
- `app/api/v1/endpoints/n8n_webhooks.py`: API endpoints
- `test_user_transactions.py`: Testing utility

### Key Variables
- `MONITORED_USER_EMAIL`: Email to monitor (hardcoded)
- `gmail_monitor.current_user_id`: User receiving transactions
- `gmail_monitor.current_user_type`: "consumer" or "business"

### Database Schema
```python
Transaction(
    user_consumer_id=current_user_id,  # For consumer users
    user_business_id=current_user_id,  # For business users
    source_type=TransactionSourceType.GMAIL,
    parsed_fields={
        'monitored_email': 'siddharth24102@iiitnr.edu.in',
        'auto_ingested': True
    }
)
```

## 🚨 Common Mistakes

❌ **Starting monitor without authentication**
✅ Call `/gmail/authenticate` first

❌ **Using wrong user token when starting monitor**
✅ Login as the user who should receive transactions

❌ **Expecting old emails to be processed**
✅ Only UNREAD emails are processed

❌ **Assuming transactions go to monitored email owner**
✅ Transactions go to user who called `/gmail/start`

## 📞 Support

If issues persist:
1. Check logs in `logs/` directory
2. Run `test_gmail_monitor.py` for diagnostic tests
3. Use `test_user_transactions.py` to verify database state
