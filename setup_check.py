"""
Setup and verify all dependencies for LUMEN features
Run this script to check and install missing packages
"""

import subprocess
import sys
import os
from pathlib import Path

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_tesseract():
    """Check if Tesseract is installed"""
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return True, path
    
    return False, None

def main():
    print("\n🔍 LUMEN Features Dependency Check")
    print("="*60)
    
    # Critical packages
    critical_packages = {
        "fastapi": "fastapi",
        "sqlalchemy": "sqlalchemy",
        "google-generativeai": "google.generativeai",
        "sentence-transformers": "sentence_transformers",
        "faiss-cpu": "faiss",
        "beautifulsoup4": "bs4",
        "pytesseract": "pytesseract",
        "opencv-python": "cv2",
        "twilio": "twilio",
        "google-api-python-client": "googleapiclient",
    }
    
    print_section("Checking Python Packages")
    
    missing_packages = []
    installed_packages = []
    
    for package, import_name in critical_packages.items():
        if check_package(package, import_name):
            print(f"✅ {package}")
            installed_packages.append(package)
        else:
            print(f"❌ {package} - NOT INSTALLED")
            missing_packages.append(package)
    
    # Check Tesseract
    print_section("Checking Tesseract OCR")
    tesseract_found, tesseract_path = check_tesseract()
    
    if tesseract_found:
        print(f"✅ Tesseract found at: {tesseract_path}")
    else:
        print("❌ Tesseract NOT found")
        print("\n⚠️  Please install Tesseract OCR:")
        print("   Download: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   Install to: C:\\Program Files\\Tesseract-OCR")
    
    # Summary
    print_section("Summary")
    print(f"Installed packages: {len(installed_packages)}/{len(critical_packages)}")
    print(f"Missing packages: {len(missing_packages)}")
    
    if missing_packages:
        print("\n⚠️  Missing packages detected!")
        print("\nWould you like to install missing packages? (y/n)")
        response = input().strip().lower()
        
        if response == 'y':
            print_section("Installing Missing Packages")
            failed_packages = []
            
            for package in missing_packages:
                print(f"\nInstalling {package}...")
                if install_package(package):
                    print(f"✅ {package} installed successfully")
                else:
                    print(f"❌ Failed to install {package}")
                    failed_packages.append(package)
            
            if failed_packages:
                print(f"\n⚠️  Failed to install: {', '.join(failed_packages)}")
                print("Please install manually:")
                print(f"pip install {' '.join(failed_packages)}")
            else:
                print("\n✅ All missing packages installed successfully!")
        else:
            print("\nTo install manually, run:")
            print(f"pip install {' '.join(missing_packages)}")
    else:
        print("\n✅ All required packages are installed!")
    
    # Check directories
    print_section("Checking Data Directories")
    
    required_dirs = [
        "data/uploads",
        "data/encrypted",
        "data/vector_store",
        "data/models",
        "credentials",
        "logs"
    ]
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✅ {dir_path}")
        else:
            print(f"⚠️  {dir_path} - Creating...")
            os.makedirs(dir_path, exist_ok=True)
            print(f"   Created {dir_path}")
    
    # Check .env file
    print_section("Checking Configuration")
    
    if os.path.exists(".env"):
        print("✅ .env file exists")
        
        # Check critical env vars
        with open(".env", "r") as f:
            env_content = f.read()
        
        critical_vars = [
            "DATABASE_URL",
            "GEMINI_API_KEY",
            "SECRET_KEY"
        ]
        
        missing_vars = []
        for var in critical_vars:
            if var not in env_content or f"{var}=" in env_content and not env_content.split(f"{var}=")[1].split("\n")[0].strip():
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing or empty variables in .env: {', '.join(missing_vars)}")
        else:
            print("✅ All critical environment variables configured")
    else:
        print("❌ .env file not found!")
        print("   Please create .env file with configuration")
    
    # Check database
    print_section("Checking Database")
    
    try:
        from app.core.database import engine
        connection = engine.connect()
        connection.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Please ensure PostgreSQL is running")
        print("   Run: python init_database.py")
    
    # Final recommendations
    print_section("Setup Status")
    
    all_good = (
        len(missing_packages) == 0 and
        tesseract_found and
        os.path.exists(".env")
    )
    
    if all_good:
        print("✅ All systems ready!")
        print("\n🚀 You can now start the server:")
        print("   python main.py")
        print("\n📝 Test the features:")
        print("   python test_features.py")
        print("\n📚 Read documentation:")
        print("   FEATURES_IMPLEMENTATION.md")
    else:
        print("⚠️  Some setup steps required:")
        if missing_packages:
            print("   1. Install missing Python packages")
        if not tesseract_found:
            print("   2. Install Tesseract OCR")
        if not os.path.exists(".env"):
            print("   3. Create .env configuration file")
        print("\nRerun this script after completing the steps.")

if __name__ == "__main__":
    main()
