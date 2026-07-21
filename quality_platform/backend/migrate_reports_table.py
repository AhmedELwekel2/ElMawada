#!/usr/bin/env python3
"""
Migration script to add the Report table to the database.
Run this script to update the database schema with the new Report table.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from models import Base

def migrate_reports_table():
    """Create the Report table in the database."""
    try:
        print("Creating Report table...")
        
        # Create all tables that don't exist yet
        Base.metadata.create_all(bind=engine)
        
        # Verify the table was created
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='reports';"))
            table_exists = result.fetchone()
            
            if table_exists:
                print("SUCCESS: Report table created successfully!")
                
                # Check table structure
                result = conn.execute(text("PRAGMA table_info(reports);"))
                columns = result.fetchall()
                print("Table structure:")
                for col in columns:
                    print(f"  {col[1]} ({col[2]})")
            else:
                print("ERROR: Failed to create Report table")
                
    except Exception as e:
        print(f"ERROR: Error during migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Starting database migration for Report table...")
    success = migrate_reports_table()
    
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)