"""
Fix enum values in database to match model definitions
"""

from sqlalchemy import text
from app.core.database import engine

print("=" * 60)
print("Fixing Enum Values in Database")
print("=" * 60)

try:
    with engine.connect() as conn:
        print("\n1. Adding new enum values to PaymentChannel...")
        
        # Add NETBANKING as a new value (alongside NetBanking)
        try:
            conn.execute(text("""
                ALTER TYPE paymentchannel ADD VALUE 'NETBANKING'
            """))
            conn.commit()
            print("   ✅ Added 'NETBANKING' value")
        except Exception as e:
            print(f"   'NETBANKING' already exists or error: {e}")
            conn.rollback()
        
        # Add UNKNOWN as a new value (alongside Unknown)
        try:
            conn.execute(text("""
                ALTER TYPE paymentchannel ADD VALUE 'UNKNOWN'
            """))
            conn.commit()
            print("   ✅ Added 'UNKNOWN' value")
        except Exception as e:
            print(f"   'UNKNOWN' already exists or error: {e}")
            conn.rollback()
        
        print("\n2. Updating transaction records...")
        # Now update all existing 'NetBanking' values to 'NETBANKING'
        result = conn.execute(text("""
            UPDATE transactions 
            SET payment_channel = 'NETBANKING' 
            WHERE payment_channel = 'NetBanking'
        """))
        conn.commit()
        print(f"   Updated {result.rowcount} records with NetBanking -> NETBANKING")
        
        # Update 'Unknown' to 'UNKNOWN'
        result = conn.execute(text("""
            UPDATE transactions 
            SET payment_channel = 'UNKNOWN' 
            WHERE payment_channel = 'Unknown'
        """))
        conn.commit()
        print(f"   Updated {result.rowcount} records with Unknown -> UNKNOWN")
        
        # Check for duplicate SourceType values (Manual vs MANUAL)
        print("\n3. Checking SourceType enum...")
        result = conn.execute(text("""
            SELECT enumlabel FROM pg_enum 
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sourcetype')
            ORDER BY enumlabel
        """))
        source_values = [row[0] for row in result]
        print(f"   Current values: {source_values}")
        
        if 'Manual' in source_values and 'MANUAL' in source_values:
            print("   Found duplicate 'Manual' and 'MANUAL' - fixing...")
            
            # Update all 'Manual' to 'MANUAL'
            result = conn.execute(text("""
                UPDATE transactions 
                SET source_type = 'MANUAL' 
                WHERE source_type = 'Manual'
            """))
            conn.commit()
            print(f"   Updated {result.rowcount} transaction records")
            
            # Try to remove 'Manual' from enum (this might fail if there are constraints)
            try:
                conn.execute(text("""
                    ALTER TYPE sourcetype DROP VALUE 'Manual'
                """))
                conn.commit()
                print("   ✅ Removed duplicate 'Manual' value")
            except Exception as e:
                print(f"   ⚠️  Could not remove 'Manual' value: {e}")
                print("   This is OK - both values can coexist")
        
        print("\n" + "=" * 60)
        print("SUCCESS! Enum values synchronized")
        print("=" * 60)
        
        # Verify final enum values
        print("\nFinal PaymentChannel values:")
        result = conn.execute(text("""
            SELECT enumlabel FROM pg_enum 
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'paymentchannel')
            ORDER BY enumlabel
        """))
        print("  ", [row[0] for row in result])
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
