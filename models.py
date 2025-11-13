"""
Database models for Interac e-Transfer web app
PostgreSQL version
"""
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Database:
    def __init__(self):
        """Initialize database connection using environment variables."""
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            # Build from individual components if DATABASE_URL not set
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'interac_transfers')
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD', 'postgres')
            self.db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        self.init_db()
    
    def get_connection(self):
        """Get database connection."""
        return psycopg2.connect(self.db_url)
    
    def init_db(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Contacts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Transfers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transfers (
                id SERIAL PRIMARY KEY,
                from_account TEXT NOT NULL,
                to_email TEXT NOT NULL,
                to_name TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                message TEXT,
                reference_number TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Account balance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_balance (
                id SERIAL PRIMARY KEY,
                account_number TEXT UNIQUE NOT NULL,
                balance REAL NOT NULL DEFAULT 5299.34,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Deposits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deposits (
                id SERIAL PRIMARY KEY,
                from_account TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Initialize account balance if not exists
        cursor.execute('SELECT COUNT(*) FROM account_balance WHERE account_number = %s', ('*** 3982',))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO account_balance (account_number, balance) 
                VALUES (%s, %s)
            ''', ('*** 3982', 5299.34))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def get_contacts(self, search: Optional[str] = None) -> List[Dict]:
        """Get all contacts, optionally filtered by search term."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if search:
            cursor.execute('''
                SELECT * FROM contacts 
                WHERE name ILIKE %s OR email ILIKE %s
                ORDER BY name
            ''', (f'%{search}%', f'%{search}%'))
        else:
            cursor.execute('SELECT * FROM contacts ORDER BY name')
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in rows]
    
    def add_contact(self, name: str, email: str) -> int:
        """Add a new contact."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO contacts (name, email) VALUES (%s, %s) RETURNING id',
                (name, email)
            )
            contact_id = cursor.fetchone()[0]
            conn.commit()
            return contact_id
        except psycopg2.IntegrityError:
            conn.rollback()
            raise ValueError(f"Contact with email {email} already exists")
        finally:
            cursor.close()
            conn.close()
    
    def get_contact(self, contact_id: int) -> Optional[Dict]:
        """Get a contact by ID."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM contacts WHERE id = %s', (contact_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(row) if row else None
    
    def create_transfer(self, from_account: str, to_email: str, to_name: str,
                       amount: float, date: str, message: str = None,
                       reference_number: str = None) -> int:
        """Create a new transfer record."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transfers 
            (from_account, to_email, to_name, amount, date, message, reference_number, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id
        ''', (from_account, to_email, to_name, amount, date, message, reference_number))
        transfer_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return transfer_id
    
    def get_transfer(self, transfer_id: int) -> Optional[Dict]:
        """Get a transfer by ID."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM transfers WHERE id = %s', (transfer_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(row) if row else None
    
    def update_transfer_status(self, transfer_id: int, status: str):
        """Update transfer status."""
        conn = self.get_connection()
        cursor = conn.cursor()
        if status == 'completed':
            cursor.execute('''
                UPDATE transfers 
                SET status = %s, completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (status, transfer_id))
        else:
            cursor.execute('''
                UPDATE transfers 
                SET status = %s
                WHERE id = %s
            ''', (status, transfer_id))
        conn.commit()
        cursor.close()
        conn.close()
    
    def get_transfers(self, limit: int = 50, days: int = 30) -> List[Dict]:
        """Get recent transfers from the last N days."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Get transfers from the last N days (completed transfers only)
        cursor.execute('''
            SELECT * FROM transfers 
            WHERE status = 'completed'
              AND (completed_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                   OR (completed_at IS NULL AND created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'))
            ORDER BY 
                CASE WHEN completed_at IS NOT NULL THEN completed_at ELSE created_at END DESC
            LIMIT %s
        ''', (days, days, limit))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_balance(self, account_number: str = '*** 3982') -> float:
        """Calculate balance from transactions (starting from 5299.34)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Starting balance
        starting_balance = 5299.34
        
        # Sum all completed transfers (subtract outgoing)
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total_outgoing
            FROM transfers 
            WHERE status = 'completed'
        ''')
        result = cursor.fetchone()
        total_outgoing = result[0] if result else 0
        
        # Sum all deposits (add incoming)
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as total_deposits
            FROM deposits
        ''')
        result = cursor.fetchone()
        total_deposits = result[0] if result else 0
        
        # Calculate current balance
        current_balance = starting_balance - total_outgoing + total_deposits
        
        cursor.close()
        conn.close()
        return current_balance
    
    def update_balance(self, amount: float, account_number: str = '*** 3982'):
        """Update account balance (subtract amount for outgoing transfer)."""
        # Note: Balance is calculated dynamically, so this method is kept for compatibility
        # but doesn't actually update a stored balance value
        pass
    
    def add_deposit(self, amount: float, from_account: str = '*** 3321'):
        """Add a deposit to the account."""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Add deposit record
        cursor.execute('''
            INSERT INTO deposits (from_account, amount)
            VALUES (%s, %s)
            RETURNING id
        ''', (from_account, amount))
        deposit_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return deposit_id
    
    def get_deposits(self, limit: int = 50, days: int = 30) -> List[Dict]:
        """Get recent deposits from the last N days."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT * FROM deposits 
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ORDER BY created_at DESC 
            LIMIT %s
        ''', (days, limit))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in rows]
