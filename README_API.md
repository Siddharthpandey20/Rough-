# LUMEN API - Frontend Developer Documentation

## Overview

LUMEN is an AI-Powered Financial Transaction Management System with anomaly detection and RAG-based chatbot capabilities. This document provides complete API documentation for frontend developers.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [End-to-End Encryption](#end-to-end-encryption)
5. [Error Handling](#error-handling)
6. [WebSocket Support](#websocket-support)

---

## Getting Started

### Base URL
```
Development: http://localhost:8000
Production: https://api.lumen.app
```

### API Version
All endpoints are prefixed with `/api/v1`

### Content Type
All requests and responses use `application/json`

---

## Authentication

### Register New User

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepass123",
  "name": "John Doe",
  "user_type": "consumer",  // or "business"
  "phone": "+919876543210",
  
  // Required for business users only
  "business_name": "Acme Corp",
  "contact_person": "Jane Smith",
  "gstin": "22AAAAA0000A1Z5"
}
```

**Response:** `201 Created`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 123,
  "user_type": "consumer"
}
```

### Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepass123",
  "user_type": "consumer"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 123,
  "user_type": "consumer"
}
```

### Logout

**Endpoint:** `POST /api/v1/auth/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

### Token Usage

Include the access token in all subsequent requests:

```javascript
headers: {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
}
```

**Token Expiration:** 30 minutes (default)

**Handling 401 Errors:** Redirect user to login page

---

## API Endpoints

### User Management

#### Get Current User Profile

**Endpoint:** `GET /api/v1/users/me`

**Headers:** Authorization required

**Response:** `200 OK`
```json
{
  "id": 123,
  "email": "user@example.com",
  "name": "John Doe",
  "phone": "+919876543210",
  "timezone": "Asia/Kolkata",
  "locale": "en",
  "currency": "INR",
  "budget_preferences": {},
  "personal_category_set": ["Groceries", "Food & Dining", "Transport", "Utilities", "Entertainment"],
  "consent_gmail_ingest": false,
  "consent_whatsapp_ingest": false,
  "consent_upi_ingest": true,
  "consent_sms_ingest": false,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_active": "2024-01-20T14:25:00Z"
}
```

#### Update User Profile

**Endpoint:** `PATCH /api/v1/users/me`

**Headers:** Authorization required

**Request Body:**
```json
{
  "name": "John Updated",
  "phone": "+919876543211",
  "personal_category_set": ["Groceries", "Food", "Transport", "Utilities", "Entertainment", "Health", "Education"]
}
```

#### Update Consent Flags

**Endpoint:** `PATCH /api/v1/users/me/consent`

**Headers:** Authorization required

**Request Body:**
```json
{
  "consent_gmail_ingest": true,
  "consent_whatsapp_ingest": false,
  "consent_upi_ingest": true,
  "consent_sms_ingest": true
}
```

---

### Transaction Management

#### Get All Transactions

**Endpoint:** `GET /api/v1/transactions`

**Headers:** Authorization required

**Query Parameters:**
- `start_date` (optional): ISO 8601 datetime
- `end_date` (optional): ISO 8601 datetime
- `category` (optional): Filter by category
- `merchant_id` (optional): Filter by merchant
- `flagged_only` (optional): boolean
- `min_amount` (optional): float
- `max_amount` (optional): float
- `source_type` (optional): Upload|Gmail|WhatsApp|UPIFeed|SMS
- `payment_channel` (optional): UPI|Card|Cash|Wallet|BankTransfer
- `limit` (optional): int (default 100, max 1000)
- `offset` (optional): int (default 0)

**Example:**
```
GET /api/v1/transactions?flagged_only=true&limit=50&offset=0
```

**Response:** `200 OK`
```json
{
  "transactions": [
    {
      "id": 456,
      "amount": 1250.50,
      "currency": "INR",
      "date": "2024-01-18T14:30:00Z",
      "merchant_name_raw": "Amazon India",
      "invoice_no": "INV-123456",
      "payment_channel": "UPI",
      "source_type": "Gmail",
      "category": "Groceries",
      "ocr_confidence": 0.95,
      "classification_confidence": 0.88,
      "flagged": true,
      "anomaly_score": 0.75,
      "anomaly_reason": "Amount exceeds 3σ threshold (z-score: 4.2)",
      "confirmed": null,
      "created_at": "2024-01-18T14:35:00Z",
      "updated_at": "2024-01-18T14:35:00Z"
    }
  ],
  "total": 127,
  "limit": 50,
  "offset": 0
}
```

#### Get Transaction by ID

**Endpoint:** `GET /api/v1/transactions/{transaction_id}`

**Headers:** Authorization required

**Response:** `200 OK` (same structure as single transaction above)

#### Get Transaction Statistics

**Endpoint:** `GET /api/v1/transactions/stats`

**Headers:** Authorization required

**Query Parameters:**
- `start_date` (optional)
- `end_date` (optional)

**Response:** `200 OK`
```json
{
  "total_transactions": 234,
  "total_amount": 125780.50,
  "avg_amount": 537.61,
  "flagged_count": 12,
  "by_category": {
    "Groceries": 45230.00,
    "Food & Dining": 28940.50,
    "Transport": 15600.00,
    "Utilities": 12800.00,
    "Entertainment": 8200.00
  },
  "by_payment_channel": {
    "UPI": 189,
    "Card": 32,
    "Cash": 13
  },
  "by_source_type": {
    "Gmail": 98,
    "Upload": 56,
    "UPIFeed": 45,
    "SMS": 35
  }
}
```

#### Confirm/Reject Flagged Transaction

**Endpoint:** `POST /api/v1/transactions/{transaction_id}/confirm`

**Headers:** Authorization required

**Request Body:**
```json
{
  "confirmed": true,  // true = confirm, false = reject
  "corrected_category": "Food & Dining",  // optional
  "notes": "This was a legitimate purchase"  // optional
}
```

**Response:** `200 OK`
```json
{
  "transaction_id": 456,
  "confirmed": true,
  "message": "Transaction confirmed successfully"
}
```

---

### Data Ingestion

#### Upload Receipt/Invoice

**Endpoint:** `POST /api/v1/ingest/upload`

**Headers:** 
- Authorization required
- Content-Type: multipart/form-data

**Form Data:**
- `file`: Image file (JPEG, PNG, PDF)
- `source_type`: "Upload"
- `metadata`: JSON string (optional)

**Example:**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('source_type', 'Upload');
formData.append('metadata', JSON.stringify({note: 'Dinner receipt'}));

fetch('/api/v1/ingest/upload', {
  method: 'POST',
  headers: {'Authorization': `Bearer ${token}`},
  body: formData
});
```

**Response:** `201 Created`
```json
{
  "source_id": 789,
  "transaction_id": 790,
  "status": "processed",
  "ocr_confidence": 0.92,
  "parsed_data": {
    "amount": 2450.00,
    "merchant_name": "Taj Restaurant",
    "date": "2024-01-19T20:15:00Z",
    "category": "Food & Dining"
  },
  "flagged": false,
  "message": "Receipt processed successfully"
}
```

#### Gmail Integration Status

**Endpoint:** `GET /api/v1/ingest/gmail/status`

**Headers:** Authorization required

**Response:** `200 OK`
```json
{
  "connected": true,
  "last_sync": "2024-01-20T10:00:00Z",
  "emails_processed": 45,
  "transactions_extracted": 38
}
```

#### Connect Gmail

**Endpoint:** `POST /api/v1/ingest/gmail/connect`

**Headers:** Authorization required

**Response:** `200 OK`
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "message": "Redirect user to auth_url for Gmail authorization"
}
```

#### WhatsApp/Twilio Webhook

**Endpoint:** `POST /api/v1/ingest/whatsapp`

**Note:** This endpoint is called by Twilio, not directly by frontend

---

### Chat & RAG

#### Start New Chat Session

**Endpoint:** `POST /api/v1/chat/session`

**Headers:** Authorization required

**Request Body:**
```json
{
  "session_metadata": {
    "device": "web",
    "locale": "en"
  }
}
```

**Response:** `201 Created`
```json
{
  "session_id": 123,
  "started_at": "2024-01-20T15:30:00Z",
  "is_active": true
}
```

#### Send Chat Message

**Endpoint:** `POST /api/v1/chat/message`

**Headers:** Authorization required

**Request Body:**
```json
{
  "message": "How much did I spend on groceries last month?",
  "session_id": 123  // optional, creates new session if not provided
}
```

**Response:** `200 OK`
```json
{
  "session_id": 123,
  "message_id": 456,
  "response": "You spent ₹8,450 on groceries last month. This includes 12 transactions, with the largest being ₹1,250 at Big Bazaar on Jan 15.",
  "intent": "summary",
  "provenance": {
    "transaction_ids": [123, 145, 167, 189, 234],
    "confidence": 0.92
  },
  "retrieved_docs": [
    {
      "id": 123,
      "amount": 1250.00,
      "merchant": "Big Bazaar",
      "category": "Groceries",
      "date": "2024-01-15T10:30:00Z",
      "relevance_score": 0.95
    }
  ],
  "timestamp": "2024-01-20T15:31:00Z"
}
```

#### Exact Transaction Lookup

**Endpoint:** `POST /api/v1/chat/exact-lookup`

**Headers:** Authorization required

**Request Body:**
```json
{
  "merchant_name": "Amazon",
  "amount": 1499.00,
  "amount_tolerance": 0.02,  // 2% tolerance
  "date": "2024-01-15T00:00:00Z",
  "date_tolerance_days": 1
}
```

**Response:** `200 OK`
```json
{
  "found": true,
  "matches": [
    {
      "id": 456,
      "amount": 1499.00,
      "merchant": "Amazon India",
      "category": "Entertainment",
      "date": "2024-01-15T14:30:00Z",
      "payment_channel": "UPI",
      "invoice_no": "171-1234567-8901234",
      "exact_match": true
    }
  ],
  "count": 1
}
```

#### Get Chat History

**Endpoint:** `GET /api/v1/chat/session/{session_id}/history`

**Headers:** Authorization required

**Response:** `200 OK`
```json
{
  "session_id": 123,
  "messages": [
    {
      "role": "user",
      "content": "Hello, my name is Siddharth",
      "created_at": "2024-01-20T15:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Hello Siddharth! How can I help you with your finances today?",
      "created_at": "2024-01-20T15:30:05Z"
    }
  ]
}
```

#### Store Persistent Memory

**Endpoint:** `POST /api/v1/chat/memory`

**Headers:** Authorization required

**Request Body:**
```json
{
  "key": "preferred_name",
  "value": "Siddharth",
  "source": "user",
  "visibility": "persistent"
}
```

**Response:** `201 Created`
```json
{
  "memory_id": 789,
  "key": "preferred_name",
  "value": "Siddharth",
  "created_at": "2024-01-20T15:32:00Z"
}
```

---

### Anomaly Detection

#### Get Flagged Transactions

**Endpoint:** `GET /api/v1/anomalies/flagged`

**Headers:** Authorization required

**Query Parameters:**
- `limit` (optional): int (default 50)
- `offset` (optional): int (default 0)
- `unconfirmed_only` (optional): boolean (default true)

**Response:** `200 OK`
```json
{
  "flagged_transactions": [
    {
      "id": 456,
      "amount": 15000.00,
      "merchant": "Luxury Store XYZ",
      "category": "Shopping",
      "date": "2024-01-19T16:45:00Z",
      "anomaly_score": 0.89,
      "anomaly_reason": "Amount significantly exceeds normal (z-score: 5.8); Isolation Forest flagged as outlier",
      "evidence": {
        "avg_monthly_spend_in_category": 3200.00,
        "std_deviation": 850.00,
                "z_score": 5.8,
        "isolation_forest_score": -0.12,
        "similar_transactions": [234, 289, 301]
      },
      "requires_action": true
    }
  ],
  "total": 8,
  "pending_review": 5
}
```

#### Get Anomaly Explanation

**Endpoint:** `GET /api/v1/anomalies/{transaction_id}/explain`

**Headers:** Authorization required

**Response:** `200 OK`
```json
{
  "transaction_id": 456,
  "explanation": "This transaction for ₹15,000 at Luxury Store XYZ is unusual because it's significantly higher than your typical spending in the Shopping category. Your average monthly spending is ₹3,200 with a standard deviation of ₹850. This transaction is 5.8 standard deviations above your normal pattern.",
  "recommendations": [
    "Verify this is a legitimate purchase",
    "Check your bank statement",
    "Contact merchant if suspicious"
  ]
}
```

---

## End-to-End Encryption (E2EE)

LUMEN implements client-side encryption where all sensitive data is encrypted on the user's device before being sent to the server.

### E2EE Implementation Flow

#### 1. Device Keypair Generation (One-time, on device)

```javascript
// Frontend code (using WebCrypto API or similar)
async function generateDeviceKeypair() {
  const keyPair = await window.crypto.subtle.generateKey(
    {
      name: "RSA-OAEP",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256"
    },
    true,
    ["encrypt", "decrypt"]
  );
  
  // Export public key to send to server
  const publicKey = await window.crypto.subtle.exportKey(
    "spki",
    keyPair.publicKey
  );
  
  // Store private key securely in IndexedDB (NEVER send to server)
  await storePrivateKeySecurely(keyPair.privateKey);
  
  return {
    publicKey: arrayBufferToBase64(publicKey),
    deviceId: generateUUID()
  };
}
```

#### 2. Register Device Public Key

**Endpoint:** `POST /api/v1/users/me/devices`

**Headers:** Authorization required

**Request Body:**
```json
{
  "device_id": "device-uuid-1234",
  "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBg...",
  "device_name": "Chrome on Windows",
  "device_type": "web"
}
```

#### 3. Encrypting Data Before Upload

```javascript
// Generate random DEK (Data Encryption Key)
function generateDEK() {
  return window.crypto.getRandomValues(new Uint8Array(32)); // 256-bit
}

// Encrypt sensitive data with DEK
async function encryptWithDEK(plaintext, dek) {
  const iv = window.crypto.getRandomValues(new Uint8Array(12));
  
  const key = await window.crypto.subtle.importKey(
    "raw",
    dek,
    "AES-GCM",
    false,
    ["encrypt"]
  );
  
  const ciphertext = await window.crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv },
    key,
    new TextEncoder().encode(plaintext)
  );
  
  return {
    ciphertext: arrayBufferToBase64(ciphertext),
    nonce: arrayBufferToBase64(iv)
  };
}

// Wrap DEK with user's public keys (for all devices)
async function wrapDEKForDevices(dek, devicePublicKeys) {
  const wrappedDEKs = {};
  
  for (const [deviceId, publicKeyPEM] of Object.entries(devicePublicKeys)) {
    const publicKey = await importPublicKey(publicKeyPEM);
    
    const wrappedDEK = await window.crypto.subtle.encrypt(
      { name: "RSA-OAEP" },
      publicKey,
      dek
    );
    
    wrappedDEKs[deviceId] = arrayBufferToBase64(wrappedDEK);
  }
  
  return wrappedDEKs;
}

// Complete encryption flow
async function encryptTransactionData(transactionData, userDevices) {
  const dek = generateDEK();
  
  const encryptedData = {
    merchant_name_raw: await encryptWithDEK(transactionData.merchant, dek),
    invoice_no: await encryptWithDEK(transactionData.invoiceNo, dek),
    parsed_fields: await encryptWithDEK(
      JSON.stringify(transactionData.parsedFields),
      dek
    )
  };
  
  const wrappedDEKs = await wrapDEKForDevices(dek, userDevices);
  
  return {
    encrypted_data: encryptedData,
    wrapped_deks: wrappedDEKs
  };
}
```

#### 4. Decrypting Received Data

```javascript
// Unwrap DEK with device's private key
async function unwrapDEK(wrappedDEK, privateKey) {
  const dek = await window.crypto.subtle.decrypt(
    { name: "RSA-OAEP" },
    privateKey,
    base64ToArrayBuffer(wrappedDEK)
  );
  
  return new Uint8Array(dek);
}

// Decrypt data with DEK
async function decryptWithDEK(encryptedData, dek) {
  const key = await window.crypto.subtle.importKey(
    "raw",
    dek,
    "AES-GCM",
    false,
    ["decrypt"]
  );
  
  const plaintext = await window.crypto.subtle.decrypt(
    {
      name: "AES-GCM",
      iv: base64ToArrayBuffer(encryptedData.nonce)
    },
    key,
    base64ToArrayBuffer(encryptedData.ciphertext)
  );
  
  return new TextDecoder().decode(plaintext);
}

// Complete decryption flow
async function decryptTransactionData(transaction, deviceId) {
  // Get private key from secure storage
  const privateKey = await getPrivateKeyFromStorage();
  
  // Unwrap DEK
  const dek = await unwrapDEK(
    transaction.wrapped_deks[deviceId],
    privateKey
  );
  
  // Decrypt fields
  const decryptedData = {
    merchant: await decryptWithDEK(transaction.encrypted_data.merchant_name_raw, dek),
    invoiceNo: await decryptWithDEK(transaction.encrypted_data.invoice_no, dek),
    parsedFields: JSON.parse(
      await decryptWithDEK(transaction.encrypted_data.parsed_fields, dek)
    )
  };
  
  return decryptedData;
}
```

### Important E2EE Notes

1. **Private keys NEVER leave the device**
2. **Server stores only:**
   - Encrypted data (ciphertext + nonce)
   - Wrapped DEKs (one per device)
   - User's public keys
3. **All decryption happens client-side**
4. **Multi-device support:** Each device has its own wrapped DEK
5. **Adding new device:** Existing device re-wraps DEKs with new device's public key

---

## Error Handling

### Standard Error Response Format

```json
{
  "error": "Error category",
  "message": "Detailed error message",
  "timestamp": "2024-01-20T15:45:00Z",
  "details": {}  // Optional additional details
}
```

### HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### Example Error Responses

**401 Unauthorized:**
```json
{
  "error": "Unauthorized",
  "message": "Invalid authentication credentials",
  "timestamp": "2024-01-20T15:45:00Z"
}
```

**422 Validation Error:**
```json
{
  "error": "Validation Error",
  "message": "Invalid input data",
  "timestamp": "2024-01-20T15:45:00Z",
  "details": {
    "email": ["Invalid email format"],
    "password": ["Password must be at least 8 characters"]
  }
}
```

---

## Rate Limiting

- **Auth endpoints:** 10 requests/minute
- **Data ingestion:** 20 uploads/hour
- **Chat:** 30 messages/minute
- **Other endpoints:** 100 requests/minute

**Rate Limit Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1642694400
```

---

## Testing & Development

### Example cURL Commands

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123","user_type":"consumer"}'
```

**Get Transactions:**
```bash
curl -X GET "http://localhost:8000/api/v1/transactions?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Send Chat Message:**
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"message":"How much did I spend last month?"}'
```

### Postman Collection

A complete Postman collection is available at: `/docs/LUMEN_API.postman_collection.json`

---

## Support & Contact

- **API Documentation:** http://localhost:8000/api/docs (Swagger UI)
- **ReDoc:** http://localhost:8000/api/redoc
- **Health Check:** http://localhost:8000/health

---

## Changelog

### Version 1.0.0 (January 2024)
- Initial release
- Complete authentication system
- Transaction management with E2EE
- RAG chatbot with stateful memory
- Anomaly detection with Isolation Forest
- Multi-source ingestion (Upload, Gmail, UPI, SMS, WhatsApp)

---

**Last Updated:** January 20, 2024
**API Version:** 1.0.0
