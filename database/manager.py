"""
Database manager module for AG Food application.
Handles all database-related operations including connection, table creation, and data management.
"""

import os
import sqlite3
from typing import Optional
from PyQt6.QtCore import pyqtSignal, QObject

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
        """Creates the necessary database tables (e.g., for products and invoices)."""
        if not self.cursor or not self.conn:
            self.database_error.emit("Database connection not established")
            return
            
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
            self.conn.commit()
            print("Products table created or already exists.")

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
            self.conn.commit()
            print("Invoices table created or already exists.")

        except sqlite3.Error as e:
            error_message = f"Error creating tables: {e}"
            print(error_message)
            self.database_error.emit(error_message)

    def close_db(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")