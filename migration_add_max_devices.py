"""
Migration script to add max_devices column to account_settings table.

Run this script to update your existing database:
    python -m backend.migration_add_max_devices
"""
from sqlalchemy import text

from .database import engine


def migrate():
    """Add max_devices column to account_settings table."""
    with engine.connect() as conn:
        # Check if column already exists (PostgreSQL syntax)
        result = conn.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name='account_settings' 
              AND column_name='max_devices'
        """))
        exists = result.scalar() > 0
        
        if exists:
            print("✓ Column 'max_devices' already exists in account_settings table.")
            return
        
        # Add the column
        conn.execute(text("""
            ALTER TABLE account_settings 
            ADD COLUMN max_devices INTEGER DEFAULT NULL
        """))
        conn.commit()
        print("✓ Successfully added 'max_devices' column to account_settings table.")
        print("\nUsage:")
        print("  - NULL or 0: Unlimited devices (default)")
        print("  - 1: Single device only")
        print("  - 2+: Limited to N devices")


if __name__ == "__main__":
    migrate()

