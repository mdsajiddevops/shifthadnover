#!/bin/bash

# Startup script for Shift Handover Application
echo "🚀 Starting Shift Handover Application..."

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
python << EOF
import time
import pymysql
import os

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        connection = pymysql.connect(
            host='db',
            user='user',
            password='password',
            database='shift_handover',
            charset='utf8mb4'
        )
        connection.close()
        print("✅ Database connection successful!")
        break
    except Exception as e:
        attempt += 1
        print(f"🔄 Database connection attempt {attempt}/{max_attempts}: {str(e)}")
        time.sleep(2)

if attempt >= max_attempts:
    print("❌ Failed to connect to database after 30 attempts")
    exit(1)
EOF

# Initialize database schema if needed
echo "🔧 Initializing database schema..."
python << EOF
try:
    import os
    from sqlalchemy import create_engine, text
    from alembic.config import Config
    from alembic import command
    
    # Connect to database
    database_url = os.environ.get('DATABASE_URL', 'mysql+pymysql://user:password@db/shift_handover')
    engine = create_engine(database_url)
    
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        
    # Initialize Alembic if not already done
    try:
        if os.path.exists('alembic.ini'):
            alembic_cfg = Config('alembic.ini')
            alembic_cfg.set_main_option('sqlalchemy.url', database_url)
            
            # Try to run migrations
            command.upgrade(alembic_cfg, 'head')
            print("✅ Database migrations applied successfully!")
        else:
            print("⚠️ alembic.ini not found, creating tables manually...")
            # Fallback to creating tables directly
            from app import app, db
            with app.app_context():
                db.create_all()
                print("✅ Database tables created!")
                
    except Exception as e:
        print(f"⚠️ Migration attempt failed, creating tables manually: {str(e)}")
        from app import app, db
        with app.app_context():
            db.create_all()
            print("✅ Database schema initialized manually")
            
except Exception as e:
    print(f"❌ Database initialization failed: {str(e)}")
    print("🔄 Continuing without database initialization...")
EOF

# Start Flask application
echo "🌟 Starting Flask application on port 5000..."
exec python app.py