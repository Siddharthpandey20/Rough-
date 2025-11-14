"""
Database initialization script
Creates databases and tables if they don't exist
"""

import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text

print("=" * 60)
print("LUMEN Database Initialization")
print("=" * 60)

# Database connection info
DB_HOST = "localhost"
DB_PORT = "5432"
DB_USER = "postgres"
DB_PASSWORD = "261104"
DB_NAME = "lumen_db"
DB_AUDIT_NAME = "lumen_audit_db"

print("\n1. Checking PostgreSQL connection...")
try:
    # Connect to PostgreSQL server (postgres database)
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    print("   [OK] Connected to PostgreSQL")
    
    # Check if databases exist
    print("\n2. Checking if databases exist...")
    
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
    main_db_exists = cursor.fetchone() is not None
    
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{DB_AUDIT_NAME}'")
    audit_db_exists = cursor.fetchone() is not None
    
    # Create main database if it doesn't exist
    if not main_db_exists:
        print(f"   Creating database: {DB_NAME}...")
        cursor.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"   [OK] Database '{DB_NAME}' created")
    else:
        print(f"   [OK] Database '{DB_NAME}' already exists")
    
    # Create audit database if it doesn't exist
    if not audit_db_exists:
        print(f"   Creating database: {DB_AUDIT_NAME}...")
        cursor.execute(f'CREATE DATABASE "{DB_AUDIT_NAME}"')
        print(f"   [OK] Database '{DB_AUDIT_NAME}' created")
    else:
        print(f"   [OK] Database '{DB_AUDIT_NAME}' already exists")
    
    cursor.close()
    conn.close()
    
    print("\n3. Creating tables...")
    
    # Import app components after database creation
    from app.core.database import engine, audit_engine, Base, AuditBase
    from app.models import user, transaction, merchant, source, pattern, chat, rag, audit
    
    # Create tables in main database
    print("   Creating tables in main database...")
    Base.metadata.create_all(bind=engine)
    print("   [OK] Main database tables created")
    
    # Create tables in audit database
    print("   Creating tables in audit database...")
    AuditBase.metadata.create_all(bind=audit_engine)
    print("   [OK] Audit database tables created")
    
    # Verify tables were created
    print("\n4. Verifying tables...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"   Main DB tables ({len(tables)}): {', '.join(tables)}")
    
    with audit_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
            ORDER BY table_name
        """))
        audit_tables = [row[0] for row in result]
        print(f"   Audit DB tables ({len(audit_tables)}): {', '.join(audit_tables)}")
    
    print("\n" + "=" * 60)
    print("SUCCESS! Database initialization complete.")
    print("=" * 60)
    print("\nYou can now:")
    print("  1. Start the server: python main.py")
    print("  2. Access Swagger UI: http://localhost:8000/api/docs")
    print("  3. Test registration endpoint")
    print("\n")
    
except psycopg2.Error as e:
    print(f"\n[ERROR] PostgreSQL Error: {e}")
    print("\nTroubleshooting:")
    print("  1. Check if PostgreSQL is running")
    print("  2. Verify username/password in .env file")
    print("  3. Ensure PostgreSQL accepts local connections")
    sys.exit(1)
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
