# LUMEN API Documentation

**Base URL:** `http://localhost:8000/api/v1`

**Swagger UI:** http://localhost:8000/api/docs

---

## 📋 Table of Contents
1. [Authentication](#authentication)
2. [Users](#users)
3. [Transactions](#transactions)
4. [Chat & RAG](#chat--rag)
5. [Data Ingestion](#data-ingestion)
6. [Anomaly Detection](#anomaly-detection)
7. [Error Responses](#error-responses)

---

## 🔐 Authentication

All endpoints (except `/auth/register` and `/auth/login`) require authentication using Bearer token.

**Header Format:**
```
Authorization: Bearer <your_access_token>
```

### 1. Register User

**Endpoint:** `POST /auth/register`

**Description:** Register a new consumer or business user

**Request Body (Consumer):**
```json
{
  "email": "user@example.com",
  "password": "SecurePass@123",
  "name": "John Doe",
  "phone": "+919876543210",
  "user_type": "consumer"
}
```

**Request Body (Business):**
```json
{
  "email": "business@example.com",
  "password": "SecurePass@123",
  "user_type": "business",
  "business_name": "ABC Enterprises Pvt Ltd",
  "contact_person": "Jane Doe",
  "gstin": "29ABCDE1234F1Z5",
  "business_type": "Retail"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 1,
  "user_type": "consumer",
  "email": "user@example.com"
}
```

---

### 2. Login

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass@123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 1,
  "user_type": "consumer",
  "email": "user@example.com"
}
```

---

### 3. Logout

**Endpoint:** `POST /auth/logout`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

---

## 👤 Users

### 1. Get Current User

**Endpoint:** `GET /users/me`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK) - Consumer:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "phone": "+919876543210",
  "user_type": "consumer",
  "timezone": "Asia/Kolkata",
  "currency": "INR",
  "is_active": true,
  "created_at": "2025-11-14T10:30:00",
  "consent_gmail_ingest": true,
  "consent_whatsapp_ingest": true
}
```

**Response (200 OK) - Business:**
```json
{
  "id": 2,
  "email": "business@example.com",
  "user_type": "business",
  "business_name": "ABC Enterprises Pvt Ltd",
  "contact_person": "Jane Doe",
  "gstin": "29ABCDE1234F1Z5",
  "business_type": "Retail",
  "is_active": true,
  "created_at": "2025-11-14T10:30:00"
}
```

---

### 2. Update User Profile

**Endpoint:** `PATCH /users/me`

**Headers:** `Authorization: Bearer <token>`

**Request Body (partial update):**
```json
{
  "name": "John Updated",
  "phone": "+919999999999",
  "timezone": "Asia/Kolkata"
}
```

**Response (200 OK):**
```json
{
  "message": "Profile updated successfully",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Updated",
    "phone": "+919999999999"
  }
}
```

---

### 3. Update Consent Settings

**Endpoint:** `PATCH /users/me/consent`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "consent_gmail_ingest": true,
  "consent_whatsapp_ingest": false
}
```

**Response (200 OK):**
```json
{
  "message": "Consent updated successfully",
  "consent_gmail_ingest": true,
  "consent_whatsapp_ingest": false
}
```

---

## 💰 Transactions

### 1. List Transactions

**Endpoint:** `GET /transactions/`

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Number of records to return (default: 50, max: 100)
- `flagged_only` (optional): Show only flagged transactions (default: false)

**Examples:**
```
GET /transactions/?skip=0&limit=20
GET /transactions/?flagged_only=true
```

**Response (200 OK):**
```json
{
  "transactions": [
    {
      "id": 1,
      "amount": 1500.50,
      "currency": "INR",
      "date": "2025-11-14T10:30:00",
      "merchant_name_raw": "BigBasket",
      "category": "Groceries",
      "payment_channel": "UPI",
      "source_type": "GMAIL",
      "invoice_no": "INV12345678",
      "flagged": false,
      "confirmed": true,
      "classification_confidence": 0.95,
      "anomaly_score": 0.15,
      "created_at": "2025-11-14T10:30:00"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 20
}
```

---

### 2. Get Transaction Statistics

**Endpoint:** `GET /transactions/stats`

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `start_date` (optional): Filter from date (YYYY-MM-DD)
- `end_date` (optional): Filter to date (YYYY-MM-DD)

**Example:**
```
GET /transactions/stats?start_date=2025-11-01&end_date=2025-11-14
```

**Response (200 OK):**
```json
{
  "total_transactions": 150,
  "total_amount": 245000.75,
  "flagged_count": 8,
  "confirmed_count": 142,
  "by_category": {
    "Groceries": {
      "count": 25,
      "total_amount": 35000.00
    },
    "Food & Dining": {
      "count": 30,
      "total_amount": 15000.00
    }
  },
  "by_payment_channel": {
    "UPI": 100,
    "CARD": 30,
    "CASH": 20
  },
  "monthly_trend": [
    {
      "month": "2025-11",
      "count": 150,
      "amount": 245000.75
    }
  ]
}
```

---

### 3. Get Single Transaction

**Endpoint:** `GET /transactions/{transaction_id}`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "id": 1,
  "amount": 1500.50,
  "currency": "INR",
  "date": "2025-11-14T10:30:00",
  "merchant_name_raw": "BigBasket",
  "category": "Groceries",
  "payment_channel": "UPI",
  "source_type": "GMAIL",
  "invoice_no": "INV12345678",
  "flagged": false,
  "confirmed": true,
  "classification_confidence": 0.95,
  "anomaly_score": 0.15,
  "merchant": {
    "id": 5,
    "name_normalized": "bigbasket",
    "name_variants": ["BigBasket", "BIGBASKET", "Big Basket"]
  },
  "parsed_fields": {
    "description": "Groceries purchase"
  }
}
```

---

### 4. Confirm Transaction

**Endpoint:** `POST /transactions/{transaction_id}/confirm`

**Headers:** `Authorization: Bearer <token>`

**Description:** Confirm a flagged transaction as legitimate

**Response (200 OK):**
```json
{
  "message": "Transaction confirmed successfully",
  "transaction_id": 1,
  "confirmed": true,
  "flagged": false
}
```

---

## 💬 Chat & RAG

### 1. Create Chat Session

**Endpoint:** `POST /chat/session`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "session_id": 1,
  "started_at": "2025-11-14T10:30:00"
}
```

---

### 2. Send Chat Message

**Endpoint:** `POST /chat/message`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "message": "How much did I spend on groceries this month?",
  "session_id": 0
}
```

**Note:** Set `session_id` to `0` to create a new session automatically.

**Response (200 OK):**
```json
{
  "session_id": 1,
  "response": "Based on your transactions, you spent ₹35,000 on groceries this month. This includes 25 transactions at stores like BigBasket, DMart, and local shops.",
  "intent": "summary",
  "confidence": 0.95,
  "provenance": {
    "transaction_ids": [1, 5, 8, 12, 15]
  },
  "retrieved_docs": [
    {
      "id": 1,
      "amount": 1500.50,
      "merchant": "BigBasket",
      "category": "Groceries",
      "date": "2025-11-14T10:30:00",
      "relevance_score": 0.95
    }
  ]
}
```

---

### 3. Get Chat History

**Endpoint:** `GET /chat/session/{session_id}/history`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "session_id": 1,
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "How much did I spend on groceries?",
      "timestamp": "2025-11-14T10:30:00"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "You spent ₹35,000 on groceries this month.",
      "intent": "summary",
      "timestamp": "2025-11-14T10:30:05",
      "provenance": {
        "transaction_ids": [1, 5, 8]
      }
    }
  ]
}
```

---

### 4. Exact Transaction Lookup

**Endpoint:** `POST /chat/exact-lookup`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "merchant_name": "BigBasket",
  "amount": 1500,
  "date": "2025-11-14"
}
```

**Note:** All fields are optional. Provide at least one.

**Response (200 OK):**
```json
{
  "matches": [
    {
      "id": 1,
      "amount": 1500.50,
      "merchant": "BigBasket",
      "date": "2025-11-14T10:30:00",
      "category": "Groceries"
    }
  ],
  "count": 1
}
```

---

### 5. Update Persistent Memory

**Endpoint:** `POST /chat/memory`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "key": "monthly_grocery_budget",
  "value": "40000"
}
```

**Response (200 OK):**
```json
{
  "message": "Memory updated successfully",
  "key": "monthly_grocery_budget",
  "value": "40000"
}
```

---

## 📥 Data Ingestion

### 1. Upload Receipt/Invoice

**Endpoint:** `POST /ingest/upload`

**Headers:** `Authorization: Bearer <token>`

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file`: Image or PDF file (required)
- `source_type`: "Upload" | "Gmail" | "WhatsApp" (optional, default: "Upload")

**Example (using curl):**
```bash
curl -X POST http://localhost:8000/api/v1/ingest/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@receipt.jpg" \
  -F "source_type=Upload"
```

**Response (200 OK):**
```json
{
  "message": "File uploaded and processed successfully",
  "source_id": 123,
  "transaction_id": 456,
  "classification": {
    "category": "Groceries",
    "confidence": 0.92
  },
  "ocr_confidence": 0.88,
  "parsed_data": {
    "amount": 1500.50,
    "merchant": "BigBasket",
    "date": "2025-11-14",
    "invoice_no": "INV12345"
  }
}
```

---

### 2. Gmail Connection Status

**Endpoint:** `GET /ingest/gmail/status`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "connected": true,
  "email": "user@gmail.com",
  "last_sync": "2025-11-14T09:00:00",
  "consent": true
}
```

---

### 3. Connect Gmail

**Endpoint:** `POST /ingest/gmail/connect`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

**Instructions:** Redirect user to `authorization_url` to authorize Gmail access.

---

### 4. Sync Gmail Transactions

**Endpoint:** `POST /ingest/gmail/sync`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "message": "Gmail sync completed",
  "transactions_found": 25,
  "transactions_created": 20,
  "last_sync": "2025-11-14T10:30:00"
}
```

---

### 5. WhatsApp Webhook

**Endpoint:** `POST /ingest/whatsapp`

**Content-Type:** `application/x-www-form-urlencoded`

**Note:** This endpoint is called by Twilio, not directly by frontend.

**Form Data:**
- `From`: WhatsApp number (e.g., "whatsapp:+919876543210")
- `Body`: Message content

**Response (200 OK):**
```json
{
  "status": "success",
  "action": "greeting"
}
```

---

### 6. Add Manual Transaction (Consumer)

**Endpoint:** `POST /ingest/manual/consumer`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "amount": 500.00,
  "paid_to": "Local Grocery Store",
  "purpose": "Weekly groceries",
  "date": "2025-11-14T10:30:00",
  "payment_method": "Cash",
  "category": "Groceries",
  "notes": "Fresh vegetables and fruits"
}
```

**Response (201 Created):**
```json
{
  "message": "Consumer transaction added successfully",
  "transaction_id": 789,
  "transaction": {
    "id": 789,
    "amount": 500.00,
    "merchant_name_raw": "Local Grocery Store",
    "category": "Groceries",
    "payment_channel": "CASH"
  }
}
```

---

### 7. Add Manual Transaction (Business)

**Endpoint:** `POST /ingest/manual/business`

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "amount": 50000.00,
  "vendor_name": "ABC Suppliers Pvt Ltd",
  "transaction_type": "Purchase",
  "date": "2025-11-14T10:30:00",
  "payment_method": "BankTransfer",
  "invoice_number": "INV/2025/001",
  "category": "Inventory",
  "description": "Raw material purchase",
  "gst_amount": 9000.00,
  "hsn_code": "1234567890"
}
```

**Response (201 Created):**
```json
{
  "message": "Business transaction added successfully",
  "transaction_id": 790,
  "transaction": {
    "id": 790,
    "amount": 50000.00,
    "merchant_name_raw": "ABC Suppliers Pvt Ltd",
    "category": "Inventory",
    "invoice_no": "INV/2025/001"
  }
}
```

---

## 🚨 Anomaly Detection

### 1. Get Flagged Transactions

**Endpoint:** `GET /anomalies/flagged`

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Number of results (default: 50)

**Response (200 OK):**
```json
{
  "flagged_transactions": [
    {
      "id": 15,
      "amount": 25000.00,
      "merchant_name_raw": "Luxury Store",
      "category": "Shopping",
      "date": "2025-11-14T10:30:00",
      "anomaly_score": 0.92,
      "flagged_reason": "Amount significantly higher than usual"
    }
  ],
  "total": 8
}
```

---

### 2. Get Anomaly Explanation

**Endpoint:** `GET /anomalies/{transaction_id}/explain`

**Headers:** `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "transaction_id": 15,
  "anomaly_score": 0.92,
  "explanation": "This transaction of ₹25,000 at Luxury Store is unusual because it's 5 times higher than your average shopping expense of ₹5,000. This category typically sees amounts between ₹1,000-₹8,000.",
  "pattern_comparison": {
    "normal_range": {
      "min": 1000,
      "max": 8000,
      "average": 5000
    },
    "this_transaction": 25000,
    "deviation_factor": 5.0
  },
  "recommendation": "Please verify this transaction. If legitimate, you can confirm it to update your spending patterns."
}
```

---

## ❌ Error Responses

All endpoints may return these standard error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to access this resource"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error message"
}
```

---

## 🔒 Security Notes

1. **Always use HTTPS** in production
2. **Store tokens securely** (e.g., httpOnly cookies, secure storage)
3. **Tokens expire** after 30 minutes by default
4. **Never expose** API keys or tokens in client-side code
5. **Validate all inputs** on frontend before sending

---

## 📊 Data Types Reference

### User Types
- `"consumer"`: Individual users
- `"business"`: Business users

### Payment Channels
- `"UPI"`
- `"CARD"`
- `"CASH"`
- `"NETBANKING"`
- `"WALLET"`

### Source Types
- `"UPLOAD"`: Manual upload
- `"GMAIL"`: Gmail integration
- `"WHATSAPP"`: WhatsApp integration
- `"MANUAL"`: Manual entry

### Transaction Types (Business)
- `"Purchase"`
- `"Sale"`
- `"Expense"`
- `"Income"`

### Chat Intents
- `"exact_lookup"`: Looking for specific transaction
- `"summary"`: Asking for aggregated data
- `"trend"`: Asking about patterns
- `"conversational"`: General chat
- `"unknown"`: Cannot determine intent

---

## 🧪 Testing

### Demo Users
After running `populate_demo_data.py`:

**Consumer:**
- Email: `demo.consumer@lumen.app`
- Password: `Demo@123`

**Business:**
- Email: `demo.business@lumen.app`
- Password: `Demo@123`

### Swagger UI
Interactive API documentation: http://localhost:8000/api/docs

### Example Flow
1. Register/Login → Get access token
2. Use token in Authorization header for all requests
3. Upload receipts or add manual transactions
4. Query transactions and statistics
5. Use chat to ask questions about spending

---

## 📞 Support

- **Swagger UI**: http://localhost:8000/api/docs
- **API Base URL**: http://localhost:8000/api/v1
- **Logs**: Check `logs/app.log` for debugging

---

**Last Updated:** November 14, 2025
