# 🚀 LUMEN - Quick Start Guide

## All Features Implemented ✅

### 1️⃣ RAG (Retrieval-Augmented Generation)
- Vector search over transactions
- Smart chat with context
- Session memory
- **Status**: ✅ Working

### 2️⃣ Gmail Integration
- OAuth2 authentication
- Auto-fetch transaction emails
- Parse bank notifications
- **Status**: ✅ Working

### 3️⃣ WhatsApp Integration
- Twilio webhook
- Transaction message parsing
- Anomaly alerts
- Bot commands
- **Status**: ✅ Working

### 4️⃣ OCR Service
- Receipt scanning
- Invoice parsing
- AI + regex fallback
- **Status**: ✅ Working

---

## 🏃‍♂️ Quick Setup

### Step 1: Check Dependencies
```powershell
python setup_check.py
```

### Step 2: Initialize Database
```powershell
python init_database.py
```

### Step 3: Start Server
```powershell
python main.py
```

### Step 4: Test Features
```powershell
python test_features.py
```

---

## 📱 API Endpoints

### Authentication
- `POST /api/v1/auth/register/consumer` - Register consumer
- `POST /api/v1/auth/register/business` - Register business
- `POST /api/v1/auth/login` - Login

### Transactions
- `GET /api/v1/transactions` - List transactions
- `GET /api/v1/transactions/{id}` - Get transaction
- `POST /api/v1/transactions/{id}/confirm` - Confirm transaction

### Ingestion
- `POST /api/v1/ingestion/upload` - Upload receipt (OCR)
- `POST /api/v1/ingestion/manual/consumer` - Manual entry (consumer)
- `POST /api/v1/ingestion/manual/business` - Manual entry (business)
- `GET /api/v1/ingestion/gmail/status` - Gmail status
- `POST /api/v1/ingestion/gmail/connect` - Connect Gmail
- `POST /api/v1/ingestion/gmail/sync` - Sync Gmail transactions
- `POST /api/v1/ingestion/whatsapp` - WhatsApp webhook

### Chat & RAG
- `POST /api/v1/chat/session` - Create chat session
- `POST /api/v1/chat/message` - Send message
- `GET /api/v1/chat/session/{id}/history` - Get history
- `POST /api/v1/chat/exact-lookup` - Database lookup
- `POST /api/v1/chat/memory` - Store memory

### Anomalies
- `GET /api/v1/anomalies` - List anomalies
- `POST /api/v1/anomalies/detect` - Detect anomalies

---

## 🔑 Environment Variables

```env
# Database
DATABASE_URL=postgresql://postgres:261104@localhost:5432/lumen_db
DATABASE_AUDIT_URL=postgresql://postgres:261104@localhost:5432/lumen_audit_db

# JWT
SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Gmail (optional)
GMAIL_CREDENTIALS_PATH=credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=credentials/gmail_token.json

# WhatsApp (optional)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# OCR
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

# RAG
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
VECTOR_STORE_PATH=data/vector_store
RAG_TOP_K=5
```

---

## 🧪 Testing Examples

### 1. Upload Receipt
```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@receipt.jpg" \
  -F "source_type=Upload"
```

### 2. Manual Transaction
```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/manual/consumer" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 150.50,
    "paid_to": "Grocery Store",
    "purpose": "Weekly shopping",
    "date": "2024-11-14T10:00:00",
    "payment_method": "cash"
  }'
```

### 3. Chat Query
```bash
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How much did I spend on food last week?",
    "session_id": 1
  }'
```

### 4. Connect Gmail
```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/gmail/connect" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Sync Gmail
```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/gmail/sync?days_back=30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📊 Swagger UI

Access interactive API docs:
```
http://localhost:8000/api/docs
```

---

## 🛠️ Troubleshooting

### Server won't start
1. Check PostgreSQL is running
2. Run `python init_database.py`
3. Verify .env configuration

### RAG not working
1. Install: `pip install sentence-transformers faiss-cpu`
2. Check logs for embedding model loading
3. Ensure `data/vector_store` exists

### Gmail not connecting
1. Create OAuth credentials in Google Cloud Console
2. Download credentials JSON
3. Place in `credentials/gmail_credentials.json`

### OCR failing
1. Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
2. Update `TESSERACT_PATH` in .env
3. Test with clear receipt images

### WhatsApp not working
1. Sign up for Twilio account
2. Configure webhook URL in Twilio console
3. Test with sandbox first

---

## 📝 Common Tasks

### Add a manual transaction
1. Login to get token
2. POST to `/api/v1/ingestion/manual/consumer` or `/business`
3. Transaction auto-categorized by AI

### Upload receipt
1. Use `/api/v1/ingestion/upload`
2. OCR extracts text
3. AI parses transaction details
4. Transaction created automatically

### Chat about spending
1. Create session: POST `/api/v1/chat/session`
2. Send message: POST `/api/v1/chat/message`
3. AI retrieves relevant transactions
4. Get natural language response

### Connect Gmail
1. POST `/api/v1/ingestion/gmail/connect`
2. Complete OAuth flow
3. POST `/api/v1/ingestion/gmail/sync`
4. Transactions auto-imported

---

## 🎯 Feature Highlights

### Smart Transaction Classification
- AI-powered categorization
- Learns from your patterns
- Confidence scores
- Manual override available

### Anomaly Detection
- Statistical analysis
- Pattern recognition
- Real-time alerts
- Human-in-the-loop review

### RAG-Powered Chat
- Ask questions in natural language
- Semantic search over transactions
- Context-aware responses
- Session memory

### Multi-Source Ingestion
- Gmail emails
- WhatsApp messages
- Receipt photos (OCR)
- Manual entry
- SMS forwarding (via WhatsApp)

---

## 📚 Documentation

- **FEATURES_IMPLEMENTATION.md** - Detailed feature guide
- **API Docs** - http://localhost:8000/api/docs
- **README.md** - Project overview
- **SETUP.md** - Installation guide

---

## 🆘 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review error messages
3. Verify configuration in `.env`
4. Run `python setup_check.py`

---

**All features are ready to use! 🎉**
