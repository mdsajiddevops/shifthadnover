#!/usr/bin/env python3
"""
Add additional_notes column to shift table
"""
import mysql.connector
import os
from datetime import datetime

def add_additional_notes_column():
    """Add additional_notes column to shift table if it doesn't exist"""
    
    connection = None
    try:
        # Database connection
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='rootpassword',
            database='shift_handover'
        )
        
        cursor = connection.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_schema = 'shift_handover' 
            AND table_name = 'shift' 
            AND column_name = 'additional_notes'
        """)
        
        result = cursor.fetchone()
        if result[0] > 0:
            print("✅ additional_notes column already exists")
            return
        
        # Add the column
        print("🔧 Adding additional_notes column to shift table...")
        cursor.execute("""
            ALTER TABLE shift 
            ADD COLUMN additional_notes TEXT NULL 
            COMMENT 'Additional notes for the handover'
        """)
        
        connection.commit()
        print("✅ Successfully added additional_notes column")
        
        # Verify the column was added
        cursor.execute("DESCRIBE shift")
        columns = cursor.fetchall()
        
        print("\n📋 Current shift table structure:")
        for column in columns:
            field, type_, null, key, default, extra = column
            print(f"  {field}: {type_} {'(NULL)' if null == 'YES' else '(NOT NULL)'}")
            
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        if connection:
            connection.rollback()
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    add_additional_notes_column()