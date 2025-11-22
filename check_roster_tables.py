
import sys
sys.path.append('/app')

from app import create_app
from flask import current_app
from sqlalchemy import inspect

def check_tables():
    app = create_app()
    with app.app_context():
        engine = current_app.extensions['migrate'].db.engine
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print("Available tables:")
        roster_tables = []
        for table in sorted(tables):
            if 'roster' in table.lower() or 'shift' in table.lower():
                roster_tables.append(table)
                print(f"  🎯 {table} (potential roster table)")
            else:
                print(f"     {table}")
        
        print(f"\nFound {len(roster_tables)} potential roster tables:")
        for table in roster_tables:
            print(f"  - {table}")
            
        return roster_tables

if __name__ == "__main__":
    check_tables()
