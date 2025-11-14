# LUMEN - AI-Powered Financial Transaction Management System

![LUMEN Logo](docs/logo.png)

> **Intelligent financial tracking with anomaly detection and conversational AI**

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- pip or conda
- Node.js 18+ (for frontend)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/lumen.git
cd lumen
```

2. **Create virtual environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up PostgreSQL databases**
```sql
CREATE DATABASE lumen_db;
CREATE DATABASE lumen_audit_db;
```

6. **Run database migrations**
```bash
alembic upgrade head
```

7. **Start the server**
```bash
python main.py
# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

8. **Access API documentation**
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- API Guide: [README_API.md](README_API.md)

## 📋 Features

### Core Functionality

- ✅ **Multi-Source Ingestion**
  - Manual upload (images, PDFs)
  - Gmail integration (invoice extraction)
  - WhatsApp/Twilio (receipt forwarding)
  - UPI transaction feeds
  - SMS parsing

- ✅ **OCR & Intelligent Parsing**
  - Tesseract OCR with preprocessing
  - Structured data extraction
  - Invoice number, amount, merchant, date
  - Multi-format support (receipts, invoices, statements)

- ✅ **AI-Powered Classification**
  - Gemini API integration
  - Per-user category customization (default 5 categories)
  - Learning from user corrections
  - Confidence scoring

- ✅ **Anomaly Detection**
  - Isolation Forest machine learning
  - Statistical 3-sigma & 6-sigma rules
  - Combined confidence scoring
  - Pattern learning per user/category

- ✅ **RAG Chatbot**
  - Stateful conversation with session memory
  - Persistent user facts
  - Hybrid retrieval (DB + vector search)
  - FAISS vector store
  - Provenance tracking

- ✅ **End-to-End Encryption (E2EE)**
  - Client-side encryption/decryption
  - Data Encryption Keys (DEK) per transaction
  - RSA key wrapping for multi-device support
  - Zero-knowledge architecture

- ✅ **Audit & Compliance**
  - Tamper-proof audit logs
  - Separate audit database
  - Chain-of-custody tracking
  - GDPR-compliant deletion

- ✅ **User Management**
  - Consumer vs Business user types
  - Custom category sets
  - Consent management
  - Multi-device support

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│  • E2EE Client Logic  • Chat UI  • Transaction Dashboard │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API (JWT Auth)
┌───────────────────────▼─────────────────────────────────┐
│                   FastAPI Backend                        │
│ ┌─────────────┐ ┌─────────────┐ ┌──────────────────────┐│
│ │  Ingestion  │ │     OCR     │ │   Classification     ││
│ │   Pipeline  │ │   Service   │ │  (Gemini API)        ││
│ └─────────────┘ └─────────────┘ └──────────────────────┘│
│ ┌─────────────┐ ┌─────────────┐ ┌──────────────────────┐│
│ │  Anomaly    │ │ RAG Service │ │   Audit Logger       ││
│ │  Detector   │ │   (FAISS)   │ │                      ││
│ └─────────────┘ └─────────────┘ └──────────────────────┘│
└───────────────────────┬─────────────────────────────────┘
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
    ┌──────────────┐         ┌──────────────┐
    │ PostgreSQL   │         │ PostgreSQL   │
    │  Main DB     │         │  Audit DB    │
    └──────────────┘         └──────────────┘
```

## 📁 Project Structure

```
lumen/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py
│   │       │   ├── users.py
│   │       │   ├── transactions.py
│   │       │   ├── chat.py
│   │       │   ├── ingestion.py
│   │       │   └── anomalies.py
│   │       └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── logging_config.py
│   ├── models/
│   │   ├── user.py
│   │   ├── transaction.py
│   │   ├── merchant.py
│   │   ├── pattern.py
│   │   ├── chat.py
│   │   ├── rag.py
│   │   ├── source.py
│   │   └── audit.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── transaction.py
│   │   └── chat.py
│   ├── services/
│   │   ├── gemini_service.py
│   │   ├── ocr_service.py
│   │   ├── anomaly_service.py
│   │   └── rag_service.py
│   └── utils/
│       ├── auth.py
│       ├── encryption.py
│       └── audit.py
├── data/
│   ├── uploads/
│   ├── encrypted/
│   ├── models/
│   └── vector_store/
├── credentials/
├── logs/
├── main.py
├── requirements.txt
├── .env.example
├── README.md
└── README_API.md
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/lumen_db
DATABASE_AUDIT_URL=postgresql://user:pass@localhost:5432/lumen_audit_db

# JWT
SECRET_KEY=<generate with: openssl rand -hex 32>
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Gemini API
GEMINI_API_KEY=<your-api-key>

# Encryption
MASTER_ENCRYPTION_KEY=<base64-encoded-key>

# External Services
TWILIO_ACCOUNT_SID=<your-twilio-sid>
TWILIO_AUTH_TOKEN=<your-twilio-token>
```

### Database Setup

```bash
# Create databases
createdb lumen_db
createdb lumen_audit_db

# Run migrations (if using Alembic)
alembic upgrade head
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py
```

## 📊 Usage Examples

### 1. Register and Login

```python
import requests

# Register
response = requests.post("http://localhost:8000/api/v1/auth/register", json={
    "email": "user@example.com",
    "password": "securepass123",
    "name": "John Doe",
    "user_type": "consumer"
})
token = response.json()["access_token"]

# All subsequent requests
headers = {"Authorization": f"Bearer {token}"}
```

### 2. Upload Receipt

```python
files = {"file": open("receipt.jpg", "rb")}
data = {"source_type": "Upload"}

response = requests.post(
    "http://localhost:8000/api/v1/ingest/upload",
    headers=headers,
    files=files,
    data=data
)
```

### 3. Chat with AI

```python
response = requests.post(
    "http://localhost:8000/api/v1/chat/message",
    headers=headers,
    json={"message": "How much did I spend on groceries last month?"}
)
print(response.json()["response"])
```

### 4. Review Flagged Transactions

```python
response = requests.get(
    "http://localhost:8000/api/v1/anomalies/flagged",
    headers=headers
)
for tx in response.json()["flagged_transactions"]:
    print(f"Flagged: ₹{tx['amount']} - {tx['anomaly_reason']}")
```

## 🔐 Security

- **JWT Authentication** with token expiration
- **End-to-End Encryption** for sensitive data
- **Password hashing** with bcrypt
- **SQL injection protection** via SQLAlchemy ORM
- **CORS configuration** for API access control
- **Rate limiting** on sensitive endpoints
- **Audit logging** for all critical operations

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

- **Backend & AI:** [Your Name]
- **Frontend:** [Frontend Developer]
- **DevOps:** [DevOps Engineer]

## 🙏 Acknowledgments

- Google Gemini API for AI capabilities
- Tesseract OCR for document processing
- FastAPI framework
- scikit-learn for machine learning
- Sentence Transformers for embeddings

## 📞 Support

- **Documentation:** [README_API.md](README_API.md)
- **Issues:** [GitHub Issues](https://github.com/yourusername/lumen/issues)
- **Email:** support@lumen.app

---

**Built with ❤️ for Hackathon 2024**
