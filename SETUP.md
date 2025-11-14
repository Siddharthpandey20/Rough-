# LUMEN Project Setup Guide

## Prerequisites Installation

### Windows Setup

1. **Python 3.10+**
```powershell
# Download from python.org or use winget
winget install Python.Python.3.11
```

2. **PostgreSQL 14+**
```powershell
# Download from postgresql.org or use chocolatey
choco install postgresql14
```

3. **Tesseract OCR**
```powershell
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
# Or use chocolatey
choco install tesseract
```

4. **Git**
```powershell
winget install Git.Git
```

## Step-by-Step Setup

### 1. Clone and Setup Environment

```powershell
# Clone repository
cd e:\Desktop\Hackasol

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```powershell
# Copy example env file
copy .env.example .env

# Edit .env file with your values
notepad .env
```

**Required Configuration:**

```ini
# Database
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/lumen_db
DATABASE_AUDIT_URL=postgresql://postgres:yourpassword@localhost:5432/lumen_audit_db

# JWT (generate secret key)
SECRET_KEY=run_this_command_to_generate
# Generate with Python:
# python -c "import secrets; print(secrets.token_hex(32))"

# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
# Get from: https://makersuite.google.com/app/apikey

# Encryption (generate master key)
MASTER_ENCRYPTION_KEY=generate_base64_key
# Generate with Python:
# python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"

# Tesseract Path (Windows)
TESSERACT_PATH=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
```

### 3. Setup PostgreSQL Databases

```powershell
# Open PostgreSQL command prompt or use pgAdmin

# Create databases
psql -U postgres
```

```sql
CREATE DATABASE lumen_db;
CREATE DATABASE lumen_audit_db;

-- Create user (optional)
CREATE USER lumen_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE lumen_db TO lumen_user;
GRANT ALL PRIVILEGES ON DATABASE lumen_audit_db TO lumen_user;

\q
```

### 4. Generate Secret Keys

```powershell
# Generate SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Generate MASTER_ENCRYPTION_KEY
python -c "import base64, os; print('MASTER_ENCRYPTION_KEY=' + base64.b64encode(os.urandom(32)).decode())"

# Copy these to your .env file
```

### 5. Initialize Database Tables

```powershell
# Run the application once to create tables
python main.py
# Press Ctrl+C after "Database tables created successfully" message
```

### 6. Start the Server

```powershell
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or simply
python main.py
```

### 7. Verify Installation

Open your browser and visit:
- API Docs: http://localhost:8000/api/docs
- Health Check: http://localhost:8000/health

## Common Issues & Solutions

### Issue 1: PostgreSQL Connection Error

**Error:** `could not connect to server`

**Solution:**
```powershell
# Check if PostgreSQL is running
Get-Service postgresql*

# Start PostgreSQL service
Start-Service postgresql-x64-14
```

### Issue 2: Tesseract Not Found

**Error:** `TesseractNotFoundError`

**Solution:**
```powershell
# Verify Tesseract installation
tesseract --version

# Update TESSERACT_PATH in .env
TESSERACT_PATH=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
```

### Issue 3: Module Not Found

**Error:** `ModuleNotFoundError: No module named 'X'`

**Solution:**
```powershell
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Or install specific package
pip install package-name
```

### Issue 4: Database Tables Not Created

**Solution:**
```powershell
# Check database connection in .env
# Verify PostgreSQL is running
# Run main.py to trigger table creation
python main.py
```

## Testing the API

### Using cURL (PowerShell)

```powershell
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"test@example.com\",\"password\":\"password123\",\"name\":\"Test User\",\"user_type\":\"consumer\"}'

# Login
$response = curl -X POST http://localhost:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"test@example.com\",\"password\":\"password123\",\"user_type\":\"consumer\"}' | ConvertFrom-Json

$token = $response.access_token

# Get user profile
curl -X GET http://localhost:8000/api/v1/users/me `
  -H "Authorization: Bearer $token"
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Register
response = requests.post(f"{BASE_URL}/auth/register", json={
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User",
    "user_type": "consumer"
})
token = response.json()["access_token"]

# Get profile
headers = {"Authorization": f"Bearer {token}"}
profile = requests.get(f"{BASE_URL}/users/me", headers=headers)
print(profile.json())
```

## Development Workflow

1. **Make code changes**
2. **Server auto-reloads** (if using `--reload`)
3. **Test in Swagger UI:** http://localhost:8000/api/docs
4. **Check logs:** `logs/app.log`
5. **Commit changes:** `git add . && git commit -m "message"`

## Next Steps

1. ✅ Complete all endpoint implementations
2. ✅ Add comprehensive error handling
3. ✅ Implement complete ingestion pipeline
4. ✅ Train initial anomaly detection models
5. ✅ Set up Gmail API credentials
6. ✅ Configure Twilio for WhatsApp
7. ✅ Add unit tests
8. ✅ Deploy to production

## Production Deployment

### Using Docker (Recommended)

```dockerfile
# Dockerfile (create this file)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```powershell
# Build and run
docker build -t lumen-api .
docker run -p 8000:8000 --env-file .env lumen-api
```

### Using Gunicorn (Linux)

```bash
pip install gunicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Support

- **GitHub Issues:** Report bugs and request features
- **Documentation:** README_API.md for complete API reference
- **Logs:** Check `logs/app.log` for debugging

---

**Happy Coding! 🚀**
