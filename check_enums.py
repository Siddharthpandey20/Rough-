"""Check all enum values in database"""
from app.core.database import engine
from sqlalchemy import text

def check_enum_values(enum_type):
    """Check what values exist in an enum"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = '{enum_type}'"))
            values = [row[0] for row in result]
            print(f"\n{enum_type}:")
            for val in values:
                print(f"  - '{val}'")
            return values
    except Exception as e:
        print(f"Error checking {enum_type}: {e}")
        return []

print("=== Current Database Enum Values ===")
check_enum_values("sourcetype")
check_enum_values("paymentchannel")
check_enum_values("usertype")
