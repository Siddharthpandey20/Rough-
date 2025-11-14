# Quick Database Setup Guide

## Step 1: Create PostgreSQL Databases

Open PowerShell and run:

```powershell
# Connect to PostgreSQL
psql -U postgres

# In psql, create the databases:
CREATE DATABASE lumen_db;
CREATE DATABASE lumen_audit_db;

# List databases to verify
\l

# Exit psql
\q
```

**OR** use pgAdmin:
1. Open pgAdmin
2. Right-click on "Databases" → Create → Database
3. Name: `lumen_db`, click Save
4. Repeat for `lumen_audit_db`

## Step 2: Run the Server

The server will automatically create all tables on startup:

```powershell
python main.py
```

**OR**

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Step 3: Test Registration

Go to: http://localhost:8000/api/docs

Try the `/auth/register` endpoint with:

```json
{
  "email": "test@example.com",
  "password": "TestPass123",
  "name": "Test User",
  "user_type": "consumer",
  "phone": "1234567890"
}
```

## Troubleshooting

### Error: "database does not exist"
- Run the SQL commands in Step 1 to create databases

### Error: "password authentication failed"
- Check your PostgreSQL password in `.env` file
- Ensure `DATABASE_URL` has the correct credentials

### Error: "could not connect to server"
- Make sure PostgreSQL service is running:
  ```powershell
  # Check status
  Get-Service -Name postgresql*
  
  # Start if stopped
  Start-Service postgresql-x64-14  # (or your version)
  ```

### Error: "peer authentication failed"
- On Linux, edit `/etc/postgresql/*/main/pg_hba.conf`
- Change `peer` to `md5` for local connections
- Restart PostgreSQL

## Current Database Configuration

From your `.env` file:
- **Main DB**: `postgresql://postgres:261104@localhost:5432/lumen_db`
- **Audit DB**: `postgresql://postgres:261104@localhost:5432/lumen_audit_db`
- **User**: postgres
- **Password**: 261104

## Verify Setup

After starting the server, check the logs for:
```
INFO:     Main database tables created successfully
INFO:     Audit database tables created successfully
```

If you see these messages, you're ready to go! 🎉
