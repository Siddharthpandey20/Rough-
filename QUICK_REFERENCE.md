# LUMEN - Quick Reference Card

## 🚀 Quick Start Commands

```powershell
# Setup
python setup.py                  # Generate keys and setup
python main.py                   # Start server
python generate_demo_data.py     # Create test data

# Access
http://localhost:8000/api/docs   # Swagger UI
http://localhost:8000/health     # Health check
```

## 🔑 Key Environment Variables

```ini
DATABASE_URL=postgresql://user:pass@localhost:5432/lumen_db
GEMINI_API_KEY=your_gemini_key
SECRET_KEY=generated_by_setup_py
MASTER_ENCRYPTION_KEY=generated_by_setup_py
```

## 📡 Essential API Endpoints

### Authentication
```
POST /api/v1/auth/register    # Register new user
POST /api/v1/auth/login       # Login
POST /api/v1/auth/logout      # Logout
```

### Transactions
```
GET  /api/v1/transactions             # List all
GET  /api/v1/transactions/{id}        # Get one
GET  /api/v1/transactions/stats       # Statistics
POST /api/v1/transactions/{id}/confirm # Confirm/reject
```

### Chat & RAG
```
POST /api/v1/chat/session        # New session
POST /api/v1/chat/message        # Send message
GET  /api/v1/chat/session/{id}/history # History
POST /api/v1/chat/exact-lookup   # Exact search
```

### Ingestion
```
POST /api/v1/ingest/upload       # Upload receipt
GET  /api/v1/ingest/gmail/status # Gmail status
POST /api/v1/ingest/gmail/connect # Connect Gmail
```

### Anomalies
```
GET  /api/v1/anomalies/flagged           # List flagged
GET  /api/v1/anomalies/{id}/explain      # Explain anomaly
```

## 🔐 Authentication Header

```javascript
headers: {
  'Authorization': 'Bearer YOUR_JWT_TOKEN'
}
```

## 📊 Demo Credentials (after running generate_demo_data.py)

```
Email: demo_consumer_1@lumen.app
Password: Demo@123
Type: consumer

Email: demo_business_1@lumen.app  
Password: Demo@123
Type: business
```

## 🏗️ Project Structure

```
app/
├── api/v1/endpoints/  # API routes
├── models/           # Database models
├── services/         # Business logic (AI, OCR, RAG)
├── utils/            # Helpers (auth, encryption, audit)
└── core/             # Config & database

main.py               # Entry point
setup.py              # Quick setup
generate_demo_data.py # Demo data
```

## 🛠️ Key Services

### Gemini Service
```python
from app.services.gemini_service import gemini_service

result = gemini_service.classify_transaction(
    merchant_name="Amazon",
    amount=1500.0,
    parsed_fields={},
    user_categories=["Groceries", "Shopping"]
)
```

### OCR Service
```python
from app.services.ocr_service import ocr_service

text, confidence = ocr_service.extract_text("receipt.jpg")
parsed = ocr_service.parse_receipt(text)
```

### Anomaly Detector
```python
from app.services.anomaly_service import anomaly_detector

is_anomaly, score, reason = anomaly_detector.detect_anomaly(
    user_id=123,
    user_type="consumer",
    transaction=transaction_obj,
    pattern=pattern_obj,
    db=db
)
```

### RAG Service
```python
from app.services.rag_service import rag_service

context = rag_service.retrieve_context(
    query="spending on groceries",
    user_id=123,
    user_type="consumer",
    db=db
)
```

## 🔒 E2EE Flow

```
Client                     Server
  │                          │
  ├─ Generate DEK            │
  ├─ Encrypt data with DEK   │
  ├─ Wrap DEK with pub key   │
  ├─────── POST ────────────>│
  │                          ├─ Store encrypted data
  │                          ├─ Store wrapped DEK
  │                          │
  │<──── GET ────────────────┤
  ├─ Unwrap DEK w/ priv key  │
  ├─ Decrypt data with DEK   │
  └─ Display plaintext       │
```

## 🧪 Testing Workflow

```powershell
# 1. Start server
python main.py

# 2. Open Swagger UI
start http://localhost:8000/api/docs

# 3. Register user
POST /auth/register

# 4. Copy token from response

# 5. Click "Authorize" button

# 6. Paste token: Bearer YOUR_TOKEN

# 7. Test endpoints
```

## 📝 Common Tasks

### Add New Endpoint
1. Create function in `app/api/v1/endpoints/*.py`
2. Add route decorator: `@router.get("/path")`
3. Include router in `app/api/v1/router.py`

### Add New Model
1. Create class in `app/models/*.py`
2. Inherit from `Base`
3. Define columns
4. Add relationships
5. Run server to create table

### Add New Service
1. Create file in `app/services/*.py`
2. Implement service class
3. Create global instance
4. Import in endpoints

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 in use | Change port: `uvicorn main:app --port 8001` |
| Database error | Check PostgreSQL running & credentials |
| Module not found | `pip install -r requirements.txt` |
| Tesseract error | Install Tesseract & update TESSERACT_PATH |
| Gemini error | Check GEMINI_API_KEY in .env |

## 📚 Documentation Files

- `README.md` - Main documentation
- `README_API.md` - Complete API reference
- `SETUP.md` - Setup instructions
- `IMPLEMENTATION_SUMMARY.md` - What's built

## 🎯 For Hackathon Demo

1. Run `python generate_demo_data.py`
2. Show Swagger UI with live endpoints
3. Demo chat: "How much did I spend?"
4. Show flagged anomalies
5. Explain E2EE architecture
6. Display audit logs

## 💡 Key Features to Highlight

✅ E2E Encryption (zero-knowledge)
✅ AI-powered classification (Gemini)
✅ Anomaly detection (ML + stats)
✅ RAG chatbot (stateful + provenance)
✅ Multi-source ingestion
✅ Audit trail (compliance)
✅ Consumer vs Business users

---

**Version:** 1.0.0 | **Status:** Production Ready
