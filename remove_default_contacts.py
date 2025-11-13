#!/usr/bin/env python3
"""
Script to remove default contacts from the database
"""
import sqlite3
from models import Database

def remove_default_contacts():
    """Remove default contacts from the database."""
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # List of default contacts to remove
    default_contacts = [
        'john.smith@example.com',
        'sarah.j@example.com',
        'mike.davis@example.com',
        'emily.wilson@example.com',
        'david.brown@example.com'
    ]
    
    print("Removing default contacts...")
    removed_count = 0
    
    for email in default_contacts:
        cursor.execute('SELECT id, name FROM contacts WHERE email = ?', (email,))
        contact = cursor.fetchone()
        if contact:
            cursor.execute('DELETE FROM contacts WHERE email = ?', (email,))
            print(f"  ✓ Removed: {contact[1]} ({email})")
            removed_count += 1
        else:
            print(f"  - Not found: {email}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Removed {removed_count} default contact(s) from the database.")
    print("Default contacts have been successfully removed!")

if __name__ == '__main__':
    try:
        remove_default_contacts()
    except Exception as e:
        print(f"❌ Error: {e}")

