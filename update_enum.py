"""Add Manual to SourceType enum and NetBanking/Unknown to PaymentChannel"""
from app.core.database import engine
from sqlalchemy import text

def check_enum_values(enum_type):
    """Check what values exist in an enum"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = '{enum_type}'"))
            values = [row[0] for row in result]
            print(f"\n{enum_type} has values: {values}")
            return values
    except Exception as e:
        print(f"Error checking {enum_type}: {e}")
        return []

def add_enum_value(enum_type, value):
    """Add value to enum type"""
    try:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TYPE {enum_type} ADD VALUE '{value}'"))
            conn.commit()
            print(f"✓ Added '{value}' to {enum_type} enum")
            return True
    except Exception as e:
        if "already exists" in str(e):
            print(f"✓ '{value}' already exists in {enum_type}")
            return True
        else:
            print(f"Error adding {value}: {e}")
            return False

print("=== Checking current enum values ===")
check_enum_values("sourcetype")
check_enum_values("paymentchannel")

print("\n=== Adding missing values ===")
# Add values one by one
add_enum_value("sourcetype", "MANUAL")
add_enum_value("paymentchannel", "NetBanking")
add_enum_value("paymentchannel", "Unknown")

print("\n=== Final enum values ===")
check_enum_values("sourcetype")
check_enum_values("paymentchannel")

print("\nEnum updates complete!")
