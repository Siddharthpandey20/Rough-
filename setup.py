"""
Quick Setup Script - Generates necessary keys and validates environment
"""

import os
import secrets
import base64
import sys


def generate_secret_key():
    """Generate a secure secret key for JWT"""
    return secrets.token_hex(32)


def generate_encryption_key():
    """Generate a master encryption key"""
    return base64.b64encode(os.urandom(32)).decode()


def check_postgresql():
    """Check if PostgreSQL is accessible"""
    try:
        import psycopg2
        return True
    except ImportError:
        return False


def create_env_file():
    """Create .env file from template with generated keys"""
    if os.path.exists('.env'):
        print("✓ .env file already exists")
        response = input("Do you want to regenerate keys? (y/N): ")
        if response.lower() != 'y':
            return
    
    print("\n🔑 Generating security keys...")
    secret_key = generate_secret_key()
    encryption_key = generate_encryption_key()
    
    print("\n📝 Creating .env file...")
    
    # Read template
    with open('.env.example', 'r') as f:
        template = f.read()
    
    # Replace placeholders
    env_content = template.replace(
        'your-secret-key-here-generate-with-openssl-rand-hex-32',
        secret_key
    ).replace(
        'your-base64-encoded-master-key-here',
        encryption_key
    )
    
    # Write .env
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✓ .env file created successfully!")
    print("\n⚠️  IMPORTANT: Please update the following in .env:")
    print("  - DATABASE_URL (PostgreSQL connection string)")
    print("  - DATABASE_AUDIT_URL (Audit DB connection string)")
    print("  - GEMINI_API_KEY (Get from https://makersuite.google.com/app/apikey)")
    print("  - TESSERACT_PATH (Path to tesseract.exe on Windows)")
    print("  - Optional: TWILIO credentials for WhatsApp integration")


def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'fastapi',
        'sqlalchemy',
        'psycopg2',
        'google.generativeai',
        'pytesseract',
        'sklearn',
        'sentence_transformers',
        'faiss'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True


def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        'data/uploads',
        'data/encrypted',
        'data/models',
        'data/vector_store',
        'credentials',
        'logs',
        'alembic/versions'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✓ {directory}")


def check_tesseract():
    """Check if Tesseract OCR is installed"""
    print("\n🔍 Checking Tesseract OCR...")
    
    import subprocess
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✓ Tesseract is installed")
            print(f"    Version: {result.stdout.split()[1]}")
            return True
    except FileNotFoundError:
        pass
    
    print("  ✗ Tesseract not found")
    print("    Download from: https://github.com/UB-Mannheim/tesseract/wiki")
    return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("🚀 LUMEN Project Setup")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required")
        print(f"   Current version: {sys.version}")
        return
    
    print(f"✓ Python {sys.version.split()[0]}")
    
    # Create directories
    create_directories()
    
    # Generate .env file
    create_env_file()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check Tesseract
    tesseract_ok = check_tesseract()
    
    # Check PostgreSQL
    print("\n🐘 Checking PostgreSQL...")
    if check_postgresql():
        print("  ✓ psycopg2 is installed")
    else:
        print("  ✗ psycopg2 not installed")
        print("    Run: pip install psycopg2-binary")
    
    print("\n" + "=" * 60)
    print("📋 Next Steps:")
    print("=" * 60)
    
    steps = [
        "1. Update .env file with your database credentials and API keys",
        "2. Create PostgreSQL databases:",
        "     CREATE DATABASE lumen_db;",
        "     CREATE DATABASE lumen_audit_db;",
        "3. Install Tesseract OCR if not already installed",
        "4. Start the server:",
        "     python main.py",
        "5. Access API docs: http://localhost:8000/api/docs"
    ]
    
    for step in steps:
        print(step)
    
    print("\n✨ Setup complete! Follow the steps above to get started.")
    print("📖 See SETUP.md for detailed instructions")


if __name__ == "__main__":
    main()
