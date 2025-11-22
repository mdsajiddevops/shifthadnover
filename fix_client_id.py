#!/usr/bin/env python3
import mysql.connector
import sys

def fix_client_id():
    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='rootpassword',
            database='shift_handover_db'
        )
        
        cursor = connection.cursor()
        
        # Update the client ID to the correct value
        update_query = """
        UPDATE sso_configs 
        SET client_id = 'oauth-client.epm-inbl.shift-handover-application.stage' 
        WHERE provider_type = 'oauth' AND provider_name = 'EPAM'
        """
        
        cursor.execute(update_query)
        connection.commit()
        
        print(f"Updated {cursor.rowcount} row(s)")
        
        # Verify the update
        verify_query = """
        SELECT provider_name, client_id 
        FROM sso_configs 
        WHERE provider_type = 'oauth' AND provider_name = 'EPAM'
        """
        
        cursor.execute(verify_query)
        result = cursor.fetchone()
        
        if result:
            print(f"Verified: {result[0]} - Client ID: {result[1]}")
        else:
            print("No EPAM OAuth configuration found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    fix_client_id()