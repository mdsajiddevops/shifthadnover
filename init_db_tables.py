from app import app, db

# Initialize Flask app context
with app.app_context():
    # Create all database tables
    db.create_all()
    print("✅ Database tables created successfully")
    
    # Print table names to verify
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"✅ Created {len(tables)} tables: {', '.join(tables)}")