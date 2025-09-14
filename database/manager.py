import os
import sqlite3
import bcrypt  # You need to install this: pip install bcrypt
from PyQt6.QtCore import pyqtSignal, QObject
import json
from typing import Optional, Dict, Union

# Define the application directory name within AppData
APP_DIR = "StockInvoiceManager"
# Define the database file name
DB_FILE_NAME = 'stock_manager.db'

class DatabaseManager(QObject):
    """
    Manages all database-related operations for the application.
    This class handles connecting, initializing, and closing the database.
    """
    database_ready = pyqtSignal()
    database_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        # Get the path to the user's AppData\Local directory
        # The user's AppData path is a standard location for application data
        # on Windows. This is a robust way to store data.
        app_data_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Local')
        # Create the full path for our application's directory
        self.app_path = os.path.join(app_data_path, APP_DIR)
        # Create the full path for the database file
        self.db_path = os.path.join(self.app_path, DB_FILE_NAME)

    def connect_db(self):
        """Connect to the SQLite database and create tables if they don't exist."""
        try:
            # Create the application directory if it doesn't exist
            os.makedirs(self.app_path, exist_ok=True)
            print(f"Application directory created at: {self.app_path}")

            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self._create_tables()
            print("Database connected and tables checked.")
            self.database_ready.emit()
        except sqlite3.Error as e:
            error_message = f"Database connection error: {e}"
            print(error_message)
            self.database_error.emit(error_message)
        except OSError as e:
            error_message = f"Error creating application directory: {e}"
            print(error_message)
            self.database_error.emit(error_message)


    def _create_tables(self):
        """Creates the necessary database tables (e.g., for products, invoices, and users)."""
        try:
            # Table for stock management (products)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    stock_quantity INTEGER NOT NULL,
                    price REAL NOT NULL
                )
            ''')
            
            # Table for storing invoice data
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT NOT NULL UNIQUE,
                    client_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    total_amount REAL NOT NULL,
                    items_json TEXT NOT NULL
                )
            ''')
            
            # New table for users with a securely hashed password
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            ''')
            self.conn.commit()
            print("All tables created or already exist.")
            self._add_default_user()
            
        except sqlite3.Error as e:
            error_message = f"Error creating tables: {e}"
            print(error_message)
            self.database_error.emit(error_message)

    def _add_default_user(self):
        """Adds a default admin user if the users table is empty."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM users")
            count = self.cursor.fetchone()[0]
            if count == 0:
                print("No users found. Creating default admin user.")
                # Hash a default password
                password = "admin"
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                
                # Insert the default admin user
                self.cursor.execute('''
                    INSERT INTO users (first_name, last_name, username, password_hash, role)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('Administrator', 'User', 'admin', hashed_password, 'admin'))
                self.conn.commit()
                print("Default 'admin' user created with password 'admin'.")
        except sqlite3.Error as e:
            print(f"Error adding default user: {e}")

    def authenticate_user(self, username, password) -> Union[Dict[str, str], bool]:
        """Authenticates a user by checking the username and password.
        Returns user details if successful, False if failed."""
        try:
            if self.cursor is None:
                print("Database cursor is not initialized.")
                return False
                
            self.cursor.execute("SELECT password_hash, first_name, last_name, role FROM users WHERE username = ?", (username,))
            result = self.cursor.fetchone()
            if result:
                password_hash, first_name, last_name, role = result
                # Check the entered password against the stored hash
                if bcrypt.checkpw(password.encode('utf-8'), password_hash):
                    print(f"User '{username}' authenticated successfully.")
                    return {
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'full_name': f"{first_name} {last_name}",
                        'role': role
                    }
            print(f"Authentication failed for user '{username}'.")
            return False
        except sqlite3.Error as e:
            print(f"Authentication database error: {e}")
            return False

    def close_db(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")
