#!/usr/bin/env python3
"""
Shift Handover Data Migration Script
Migrates data from old application to new version

Usage:
    python migrate_data.py --action export --source old
    python migrate_data.py --action import --target new
    python migrate_data.py --action verify
    python migrate_data.py --action full-migration
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, date
from decimal import Decimal
import traceback

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================

OLD_DB_CONFIG = {
    'type': 'postgresql',  # postgresql, mysql, sqlite
    'host': 'OLD_SERVER_IP',
    'port': 5432,
    'database': 'shift_handover_old',
    'user': 'DB_USER',
    'password': 'DB_PASSWORD'
}

NEW_DB_CONFIG = {
    'type': 'postgresql',  # postgresql, mysql, sqlite
    'host': 'localhost',
    'port': 5432,
    'database': 'shift_handover',
    'user': 'DB_USER',
    'password': 'DB_PASSWORD'
}

# Tables to migrate in order (respects foreign key dependencies)
MIGRATION_ORDER = [
    # Phase 1: Core Reference Data
    'account',
    'team',
    'user',
    'team_member',
    'user_team_memberships',
    
    # Phase 2: Shift Handover Reports
    'shift',
    'incident',
    'shift_key_point',
    'shift_key_point_update',
    'shift_change_info',
    'shift_kb_update',
    'current_shift_engineers',
    'next_shift_engineers',
    
    # Phase 3: Enhanced Handover
    'handover_request',
    'incident_assignment',
    'incident_assignment_response',
    'handover_incident_response_log',
    'handover_response',
    'handover_notification',
    'handover_audit_log',
    
    # Phase 4: Roster Data
    'shift_roster',
    'team_shift_configs',
    'roster_assignments',
    'checkin_log',
    
    # Phase 5: Swap/Leave
    'shift_swap_request',
    'leave_request',
    'swap_leave_notification',
    'swap_leave_audit_log',
    
    # Phase 6: Configuration
    'app_config',
    'team_email_config',
    'escalation_matrix_file',
    'application_detail',
    'kb_detail',
    'vendor_detail',
]

# ============================================
# SETUP
# ============================================

# Create directories
EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Setup logging
log_filename = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, log_filename)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# DATABASE CONNECTIONS
# ============================================

def get_db_connection(config):
    """Get database connection based on config"""
    db_type = config.get('type', 'postgresql')
    
    if db_type == 'postgresql':
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['user'],
                password=config['password']
            )
            return conn
        except ImportError:
            logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
            sys.exit(1)
    
    elif db_type == 'mysql':
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['user'],
                password=config['password']
            )
            return conn
        except ImportError:
            logger.error("mysql-connector-python not installed. Run: pip install mysql-connector-python")
            sys.exit(1)
    
    elif db_type == 'sqlite':
        import sqlite3
        conn = sqlite3.connect(config['database'])
        conn.row_factory = sqlite3.Row
        return conn
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def json_serializer(obj):
    """Custom JSON serializer for dates and decimals"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ============================================
# EXPORT FUNCTIONS
# ============================================

def export_table(conn, table_name, db_type='postgresql'):
    """Export a single table to JSON"""
    logger.info(f"Exporting table: {table_name}")
    
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        if db_type == 'postgresql':
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            exists = cursor.fetchone()[0]
        elif db_type == 'mysql':
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            exists = cursor.fetchone() is not None
        else:  # sqlite
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            exists = cursor.fetchone() is not None
        
        if not exists:
            logger.warning(f"Table {table_name} does not exist, skipping...")
            return None
        
        # Get column names
        if db_type in ['postgresql', 'mysql']:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
            columns = [desc[0] for desc in cursor.description]
        else:  # sqlite
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
        
        # Export data
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        data = []
        for row in rows:
            if db_type == 'sqlite':
                row_dict = {columns[i]: row[i] for i in range(len(columns))}
            else:
                row_dict = dict(zip(columns, row))
            data.append(row_dict)
        
        # Save to JSON file
        export_file = os.path.join(EXPORT_DIR, f"{table_name}.json")
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump({
                'table': table_name,
                'columns': columns,
                'row_count': len(data),
                'exported_at': datetime.now().isoformat(),
                'data': data
            }, f, default=json_serializer, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Exported {len(data)} rows from {table_name}")
        return len(data)
    
    except Exception as e:
        logger.error(f"❌ Error exporting {table_name}: {str(e)}")
        return None
    finally:
        cursor.close()


def export_all_tables(config):
    """Export all tables from source database"""
    logger.info("=" * 60)
    logger.info("STARTING DATA EXPORT")
    logger.info("=" * 60)
    
    conn = get_db_connection(config)
    db_type = config.get('type', 'postgresql')
    
    results = {}
    total_rows = 0
    
    for table in MIGRATION_ORDER:
        count = export_table(conn, table, db_type)
        results[table] = count
        if count:
            total_rows += count
    
    conn.close()
    
    # Save summary
    summary = {
        'export_time': datetime.now().isoformat(),
        'source_config': {k: v for k, v in config.items() if k != 'password'},
        'tables': results,
        'total_rows': total_rows
    }
    
    with open(os.path.join(EXPORT_DIR, '_export_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info("=" * 60)
    logger.info(f"EXPORT COMPLETE: {total_rows} total rows from {len([r for r in results.values() if r])} tables")
    logger.info("=" * 60)
    
    return results


# ============================================
# IMPORT FUNCTIONS
# ============================================

def import_table(conn, table_name, db_type='postgresql'):
    """Import a single table from JSON"""
    logger.info(f"Importing table: {table_name}")
    
    export_file = os.path.join(EXPORT_DIR, f"{table_name}.json")
    
    if not os.path.exists(export_file):
        logger.warning(f"Export file for {table_name} not found, skipping...")
        return None
    
    with open(export_file, 'r', encoding='utf-8') as f:
        export_data = json.load(f)
    
    data = export_data.get('data', [])
    columns = export_data.get('columns', [])
    
    if not data:
        logger.info(f"No data to import for {table_name}")
        return 0
    
    cursor = conn.cursor()
    
    try:
        # Check if table exists in target
        if db_type == 'postgresql':
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            exists = cursor.fetchone()[0]
        elif db_type == 'mysql':
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            exists = cursor.fetchone() is not None
        else:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            exists = cursor.fetchone() is not None
        
        if not exists:
            logger.warning(f"Table {table_name} does not exist in target database, skipping...")
            return None
        
        # Get target table columns
        if db_type in ['postgresql', 'mysql']:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
            target_columns = [desc[0] for desc in cursor.description]
        else:
            cursor.execute(f"PRAGMA table_info({table_name})")
            target_columns = [row[1] for row in cursor.fetchall()]
        
        # Find common columns
        common_columns = [col for col in columns if col in target_columns]
        
        if not common_columns:
            logger.error(f"No matching columns found for {table_name}")
            return None
        
        # Build insert query
        placeholders = ', '.join(['%s' if db_type != 'sqlite' else '?' for _ in common_columns])
        columns_str = ', '.join(common_columns)
        
        if db_type == 'postgresql':
            insert_query = f"""
                INSERT INTO {table_name} ({columns_str}) 
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
        elif db_type == 'mysql':
            insert_query = f"""
                INSERT IGNORE INTO {table_name} ({columns_str}) 
                VALUES ({placeholders})
            """
        else:
            insert_query = f"""
                INSERT OR IGNORE INTO {table_name} ({columns_str}) 
                VALUES ({placeholders})
            """
        
        # Import rows
        imported = 0
        errors = 0
        
        for row in data:
            try:
                values = [row.get(col) for col in common_columns]
                cursor.execute(insert_query, values)
                imported += 1
            except Exception as e:
                errors += 1
                if errors <= 5:  # Log first 5 errors
                    logger.warning(f"Error importing row in {table_name}: {str(e)}")
        
        conn.commit()
        
        if errors:
            logger.warning(f"⚠️ Imported {imported} rows with {errors} errors in {table_name}")
        else:
            logger.info(f"✅ Imported {imported} rows into {table_name}")
        
        return imported
    
    except Exception as e:
        logger.error(f"❌ Error importing {table_name}: {str(e)}")
        conn.rollback()
        return None
    finally:
        cursor.close()


def import_all_tables(config):
    """Import all tables to target database"""
    logger.info("=" * 60)
    logger.info("STARTING DATA IMPORT")
    logger.info("=" * 60)
    
    conn = get_db_connection(config)
    db_type = config.get('type', 'postgresql')
    
    results = {}
    total_rows = 0
    
    for table in MIGRATION_ORDER:
        count = import_table(conn, table, db_type)
        results[table] = count
        if count:
            total_rows += count
    
    conn.close()
    
    # Save summary
    summary = {
        'import_time': datetime.now().isoformat(),
        'target_config': {k: v for k, v in config.items() if k != 'password'},
        'tables': results,
        'total_rows': total_rows
    }
    
    with open(os.path.join(EXPORT_DIR, '_import_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info("=" * 60)
    logger.info(f"IMPORT COMPLETE: {total_rows} total rows into {len([r for r in results.values() if r])} tables")
    logger.info("=" * 60)
    
    return results


# ============================================
# VERIFICATION FUNCTIONS
# ============================================

def verify_migration():
    """Verify migration by comparing source and target counts"""
    logger.info("=" * 60)
    logger.info("VERIFYING MIGRATION")
    logger.info("=" * 60)
    
    # Load summaries
    export_summary_file = os.path.join(EXPORT_DIR, '_export_summary.json')
    import_summary_file = os.path.join(EXPORT_DIR, '_import_summary.json')
    
    if not os.path.exists(export_summary_file):
        logger.error("Export summary not found. Run export first.")
        return False
    
    if not os.path.exists(import_summary_file):
        logger.error("Import summary not found. Run import first.")
        return False
    
    with open(export_summary_file, 'r') as f:
        export_summary = json.load(f)
    
    with open(import_summary_file, 'r') as f:
        import_summary = json.load(f)
    
    # Compare counts
    all_match = True
    
    print("\n" + "=" * 70)
    print(f"{'Table':<35} {'Exported':>12} {'Imported':>12} {'Status':>8}")
    print("=" * 70)
    
    for table in MIGRATION_ORDER:
        exported = export_summary.get('tables', {}).get(table)
        imported = import_summary.get('tables', {}).get(table)
        
        if exported is None and imported is None:
            status = "SKIP"
        elif exported == imported:
            status = "✅ OK"
        elif imported is None:
            status = "⚠️ MISS"
            all_match = False
        elif exported > imported:
            status = "⚠️ LESS"
            all_match = False
        else:
            status = "✅ OK+"
        
        exported_str = str(exported) if exported is not None else "-"
        imported_str = str(imported) if imported is not None else "-"
        
        print(f"{table:<35} {exported_str:>12} {imported_str:>12} {status:>8}")
    
    print("=" * 70)
    
    total_exported = export_summary.get('total_rows', 0)
    total_imported = import_summary.get('total_rows', 0)
    
    print(f"\nTotal Exported: {total_exported}")
    print(f"Total Imported: {total_imported}")
    
    if all_match:
        logger.info("✅ VERIFICATION PASSED: All data migrated successfully!")
    else:
        logger.warning("⚠️ VERIFICATION WARNING: Some data may not have been migrated")
    
    return all_match


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description='Shift Handover Data Migration Tool')
    parser.add_argument('--action', required=True, 
                       choices=['export', 'import', 'verify', 'full-migration'],
                       help='Action to perform')
    parser.add_argument('--source', default='old', help='Source: old or new')
    parser.add_argument('--target', default='new', help='Target: old or new')
    
    args = parser.parse_args()
    
    try:
        if args.action == 'export':
            config = OLD_DB_CONFIG if args.source == 'old' else NEW_DB_CONFIG
            export_all_tables(config)
        
        elif args.action == 'import':
            config = NEW_DB_CONFIG if args.target == 'new' else OLD_DB_CONFIG
            import_all_tables(config)
        
        elif args.action == 'verify':
            verify_migration()
        
        elif args.action == 'full-migration':
            logger.info("Starting full migration process...")
            
            # Step 1: Export
            logger.info("\n>>> STEP 1: Exporting from old database...")
            export_all_tables(OLD_DB_CONFIG)
            
            # Step 2: Import
            logger.info("\n>>> STEP 2: Importing to new database...")
            import_all_tables(NEW_DB_CONFIG)
            
            # Step 3: Verify
            logger.info("\n>>> STEP 3: Verifying migration...")
            verify_migration()
            
            logger.info("\n🎉 FULL MIGRATION COMPLETE!")
    
    except KeyboardInterrupt:
        logger.info("\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()




