import os
import sqlite3
import bcrypt  # You need to install this: pip install bcrypt
from PyQt6.QtCore import pyqtSignal, QObject
import json
from typing import Optional, Dict, Union, Any

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
        self.current_user: Optional[str] = None
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
                    barcode TEXT UNIQUE,
                    sku TEXT UNIQUE,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    category TEXT,
                    reorder_point INTEGER DEFAULT 0,
                    price REAL NOT NULL,
                    supplier_id INTEGER,
                    stock_quantity INTEGER NOT NULL,
                    current_stock_quantity INTEGER DEFAULT 0
                )
            ''')
            
            # Table for storing invoice data
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT NOT NULL UNIQUE,
                    client_name TEXT,
                    client_id INTEGER,
                    date TEXT NOT NULL,
                    total_amount REAL NOT NULL,
                    items_json TEXT NOT NULL
                )
            ''')
            
            # Suppliers (master data)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    contact_info TEXT
                )
            ''')
            
            # Clients master data
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    address_line TEXT,
                    city TEXT,
                    state TEXT,
                    postal_code TEXT,
                    country TEXT,
                    dob TEXT,
                    gender TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(email)
                )
            ''')
            
            # Payments made by clients, optionally linked to invoice
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS client_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    invoice_id INTEGER,
                    amount REAL NOT NULL,
                    method TEXT,
                    reference TEXT,
                    timestamp TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE SET NULL
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS business_info (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    business_name TEXT,
                    address_line TEXT,
                    phone_landline TEXT,
                    phone_mobile TEXT,
                    fax_number TEXT,
                    email_address TEXT,
                    bank_identity_statement TEXT,
                    bank_name TEXT,
                    common_company_identifier TEXT,
                    tax_identifier TEXT,
                    trade_register_number TEXT,
                    patente_number TEXT
                )
            ''')

            
            # Stock movements (transactional data)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    movement_type TEXT,
                    reason TEXT,
                    reference_id INTEGER,
                    location_id INTEGER,
                    batch_id INTEGER,
                    unit TEXT,
                    unit_qty REAL,
                    cost_per_unit REAL,
                    user TEXT,
                    timestamp TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            ''')

            # Locations (warehouses/rooms)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    kind TEXT
                )
            ''')

            # Batches/Lots with expiry and block status
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    batch_no TEXT NOT NULL,
                    expiry_date TEXT,
                    blocked INTEGER DEFAULT 0,
                    UNIQUE(product_id, batch_no),
                    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
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
            
            # Ensure optional columns exist on invoices (client_id)
            try:
                self.cursor.execute("PRAGMA table_info(invoices)")
                inv_cols = [row[1] for row in self.cursor.fetchall()]
                if 'client_id' not in inv_cols:
                    self.cursor.execute("ALTER TABLE invoices ADD COLUMN client_id INTEGER")
                    self.conn.commit()
            except Exception:
                pass

            # Create index to speed up invoice lookups by date/number
            try:
                self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(date)")
                self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number)")
                self.conn.commit()
            except Exception:
                pass
            print("All tables created or already exist.")
            self._add_default_user()
            # Ensure new columns exist if upgrading from older schema
            self._ensure_products_schema()
            self._ensure_business_info_schema()
            
        except sqlite3.Error as e:
            error_message = f"Error creating tables: {e}"
            print(error_message)
            self.database_error.emit(error_message)

    def _ensure_products_schema(self):
        """Ensure products and related tables have expected columns for upgraded installs."""
        try:
            self.cursor.execute("PRAGMA table_info(products)")
            cols = [row[1] for row in self.cursor.fetchall()]
            to_add = []
            if 'barcode' not in cols:
                to_add.append("ALTER TABLE products ADD COLUMN barcode TEXT UNIQUE")
            if 'sku' not in cols:
                to_add.append("ALTER TABLE products ADD COLUMN sku TEXT UNIQUE")
            if 'reorder_point' not in cols:
                to_add.append("ALTER TABLE products ADD COLUMN reorder_point INTEGER DEFAULT 0")
            if 'category' not in cols:
                to_add.append("ALTER TABLE products ADD COLUMN category TEXT")
            if 'uom' not in cols:
                to_add.append("ALTER TABLE products ADD COLUMN uom TEXT")
            if 'supplier_id' not in cols:
                to_add.append("ALTER TABLE products ADD COLUMN supplier_id INTEGER")
            if 'current_stock_quantity' not in cols:
                to_add.append("ALTER TABLE products ADD COLUMN current_stock_quantity INTEGER DEFAULT 0")
            for stmt in to_add:
                self.cursor.execute(stmt)
            if to_add:
                self.conn.commit()
            # Initialize current_stock_quantity from legacy stock_quantity if present
            if 'stock_quantity' in cols and 'current_stock_quantity' in cols:
                self.cursor.execute(
                    "UPDATE products SET current_stock_quantity = COALESCE(current_stock_quantity, stock_quantity)"
                )
                self.conn.commit()
            # Create suppliers, stock_movements, locations, batches if missing
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                contact_info TEXT
            )''')
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                movement_type TEXT,
                reason TEXT,
                reference_id INTEGER,
                location_id INTEGER,
                batch_id INTEGER,
                unit TEXT,
                unit_qty REAL,
                cost_per_unit REAL,
                user TEXT,
                timestamp TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            )''')
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                kind TEXT
            )''')
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                batch_no TEXT NOT NULL,
                expiry_date TEXT,
                blocked INTEGER DEFAULT 0,
                UNIQUE(product_id, batch_no),
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            )''')
            self.conn.commit()
            # Ensure optional columns exist on batches
            try:
                self.cursor.execute("PRAGMA table_info(batches)")
                bcols = [row[1] for row in self.cursor.fetchall()]
                if 'mfg_date' not in bcols:
                    self.cursor.execute("ALTER TABLE batches ADD COLUMN mfg_date TEXT")
                    self.conn.commit()
            except sqlite3.Error:
                pass
        except sqlite3.Error as e:
            print(f"Error ensuring products schema: {e}")

    def _ensure_business_info_schema(self):
        """Ensure business_info table contains the latest optional columns."""
        try:
            self.cursor.execute("PRAGMA table_info(business_info)")
            cols = [row[1] for row in self.cursor.fetchall()]
            statements = []
            if 'address_line' not in cols:
                statements.append("ALTER TABLE business_info ADD COLUMN address_line TEXT")
            if 'phone_landline' not in cols:
                statements.append("ALTER TABLE business_info ADD COLUMN phone_landline TEXT")
            if 'phone_mobile' not in cols:
                statements.append("ALTER TABLE business_info ADD COLUMN phone_mobile TEXT")
            if 'fax_number' not in cols:
                statements.append("ALTER TABLE business_info ADD COLUMN fax_number TEXT")
            if 'email_address' not in cols:
                statements.append("ALTER TABLE business_info ADD COLUMN email_address TEXT")
            if 'patente_number' not in cols:
                statements.append("ALTER TABLE business_info ADD COLUMN patente_number TEXT")
            for stmt in statements:
                try:
                    self.cursor.execute(stmt)
                except sqlite3.Error:
                    pass
            if statements:
                self.conn.commit()
        except sqlite3.Error as e:
            print(f"DB error ensuring business_info schema: {e}")


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

    # ------------------ Products API ------------------
    def list_products(self, search: Optional[str] = None, location_id: Optional[int] = None):
        """Return all products, with qty for a specific location or global, including category and reorder point."""
        try:
            if search:
                like = f"%{search}%"
                if location_id is None:
                    self.cursor.execute(
                        "SELECT id, barcode, sku, name, category, current_stock_quantity, price, reorder_point, uom FROM products WHERE name LIKE ? OR description LIKE ? OR barcode LIKE ? OR sku LIKE ? OR category LIKE ? ORDER BY name ASC",
                        (like, like, like, like, like),
                    )
                else:
                    self.cursor.execute(
                        "SELECT id, barcode, sku, name, category, (SELECT COALESCE(SUM(quantity),0) FROM stock_movements sm WHERE sm.product_id = products.id AND sm.location_id = ?) AS qty, price, reorder_point, uom FROM products WHERE name LIKE ? OR description LIKE ? OR barcode LIKE ? OR sku LIKE ? OR category LIKE ? ORDER BY name ASC",
                        (location_id, like, like, like, like, like),
                    )
            else:
                if location_id is None:
                    self.cursor.execute(
                        "SELECT id, barcode, sku, name, category, current_stock_quantity, price, reorder_point, uom FROM products ORDER BY name ASC"
                    )
                else:
                    self.cursor.execute(
                        "SELECT id, barcode, sku, name, category, (SELECT COALESCE(SUM(quantity),0) FROM stock_movements sm WHERE sm.product_id = products.id AND sm.location_id = ?) AS qty, price, reorder_point, uom FROM products ORDER BY name ASC",
                        (location_id,),
                    )
            rows = self.cursor.fetchall()
            return rows or []
        except sqlite3.Error as e:
            print(f"Error listing products: {e}")
            return []

    def add_product(self, name: str, description: str, stock_quantity: int, price: float, barcode: Optional[str] = None,
                    sku: Optional[str] = None, reorder_point: int = 0, supplier_id: Optional[int] = None,
                    category: Optional[str] = None) -> Optional[int]:
        """Insert a product and log initial stock movement. Returns new product id or None on error."""
        try:
            self.cursor.execute(
                "INSERT INTO products (barcode, sku, name, description, category, reorder_point, price, supplier_id, stock_quantity, current_stock_quantity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (barcode, sku, name, description, category, reorder_point, price, supplier_id, stock_quantity, stock_quantity),
            )
            self.conn.commit()
            new_id = self.cursor.lastrowid
            # Log initial stock if any
            if stock_quantity != 0:
                self._log_stock_movement(new_id, stock_quantity, 'Initial', None)
            return new_id
        except sqlite3.IntegrityError as e:
            print(f"Integrity error adding product (maybe duplicate name): {e}")
            return None
        except sqlite3.Error as e:
            print(f"DB error adding product: {e}")
            return None

    def update_product(self, product_id: int, name: str, description: str, stock_quantity: int, price: float,
                        barcode: Optional[str] = None, sku: Optional[str] = None, reorder_point: Optional[int] = None,
                        supplier_id: Optional[int] = None, category: Optional[str] = None) -> bool:
        """Update product master fields; adjust stock via movement if quantity changed."""
        try:
            # Get current qty to compute delta
            self.cursor.execute("SELECT current_stock_quantity FROM products WHERE id = ?", (product_id,))
            row = self.cursor.fetchone()
            current_qty = int(row[0]) if row else 0
            delta = int(stock_quantity) - current_qty
            self.cursor.execute(
                "UPDATE products SET barcode = COALESCE(?, barcode), sku = COALESCE(?, sku), name = ?, description = ?, category = COALESCE(?, category), reorder_point = COALESCE(?, reorder_point), price = ?, supplier_id = COALESCE(?, supplier_id), current_stock_quantity = ? WHERE id = ?",
                (barcode, sku, name, description, category, reorder_point, price, supplier_id, stock_quantity, product_id),
            )
            self.conn.commit()
            if delta != 0:
                # Log as Adjustment
                self._log_stock_movement(product_id, delta, 'Adjustment', None)
            return self.cursor.rowcount > 0
        except sqlite3.IntegrityError as e:
            print(f"Integrity error updating product: {e}")
            return False
        except sqlite3.Error as e:
            print(f"DB error updating product: {e}")
            return False

    def delete_product(self, product_id: int) -> bool:
        """Delete product by id."""
        try:
            # Delete movements first to keep things tidy
            self.cursor.execute("DELETE FROM stock_movements WHERE product_id = ?", (product_id,))
            self.cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB error deleting product: {e}")
            return False

    def adjust_stock(self, product_id: int, delta: int, movement_type: str = 'Adjustment', reference_id: Optional[int] = None,
                     *, reason: Optional[str] = None, location_id: Optional[int] = None, batch_id: Optional[int] = None,
                     unit: Optional[str] = None, unit_qty: Optional[float] = None, cost_per_unit: Optional[float] = None) -> bool:
        """Increment/decrement stock by delta (base units). Logs stock_movements with optional reason/location/batch and updates cached current stock."""
        try:
            # Ensure stock does not go below zero
            self.cursor.execute("SELECT current_stock_quantity FROM products WHERE id = ?", (product_id,))
            row = self.cursor.fetchone()
            if not row:
                return False
            new_qty = int(row[0]) + int(delta)
            if new_qty < 0:
                return False
            self.cursor.execute(
                "UPDATE products SET current_stock_quantity = ? WHERE id = ?",
                (new_qty, product_id),
            )
            self.conn.commit()
            # Log movement
            if delta != 0:
                self._log_stock_movement(product_id, delta, movement_type, reference_id, reason=reason, location_id=location_id, batch_id=batch_id, unit=unit, unit_qty=unit_qty, cost_per_unit=cost_per_unit)
            return True
        except sqlite3.Error as e:
            print(f"DB error adjusting stock: {e}")
            return False

    def _log_stock_movement(self, product_id: int, quantity: int, movement_type: str, reference_id: Optional[int], *, reason: Optional[str] = None,
                             location_id: Optional[int] = None, batch_id: Optional[int] = None, unit: Optional[str] = None,
                             unit_qty: Optional[float] = None, cost_per_unit: Optional[float] = None) -> None:
        try:
            self.cursor.execute(
                "INSERT INTO stock_movements (product_id, quantity, movement_type, reason, reference_id, location_id, batch_id, unit, unit_qty, cost_per_unit, user) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (product_id, int(quantity), movement_type, reason, reference_id, location_id, batch_id, unit, unit_qty, cost_per_unit, self.current_user),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"DB error logging stock movement: {e}")

    # -------- Batch / Lot API --------
    def add_batch(self, product_id: int, batch_no: str, expiry_date: Optional[str] = None) -> Optional[int]:
        try:
            self.cursor.execute(
                "INSERT INTO batches (product_id, batch_no, expiry_date) VALUES (?, ?, ?)",
                (product_id, batch_no, expiry_date),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"DB error adding batch: {e}")
            return None

    def list_batches(self, product_id: int, include_blocked: bool = False):
        try:
            if include_blocked:
                self.cursor.execute("SELECT id, batch_no, expiry_date, blocked FROM batches WHERE product_id = ? ORDER BY expiry_date IS NULL, expiry_date ASC", (product_id,))
            else:
                self.cursor.execute("SELECT id, batch_no, expiry_date, blocked FROM batches WHERE product_id = ? AND COALESCE(blocked,0)=0 ORDER BY expiry_date IS NULL, expiry_date ASC", (product_id,))
            return self.cursor.fetchall() or []
        except sqlite3.Error as e:
            print(f"DB error listing batches: {e}")
            return []

    def set_batch_blocked(self, batch_id: int, blocked: bool = True) -> bool:
        try:
            self.cursor.execute("UPDATE batches SET blocked = ? WHERE id = ?", (1 if blocked else 0, batch_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB error blocking batch: {e}")
            return False

    # -------- Locations API --------
    def add_location(self, name: str, kind: str = "") -> Optional[int]:
        try:
            self.cursor.execute("INSERT INTO locations (name, kind) VALUES (?, ?)", (name, kind))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"DB error adding location: {e}")
            return None

    def list_locations(self):
        try:
            self.cursor.execute("SELECT id, name, kind FROM locations ORDER BY name ASC")
            return self.cursor.fetchall() or []
        except sqlite3.Error as e:
            print(f"DB error listing locations: {e}")
            return []

    # -------- Clients API --------
    def add_client(self, *, full_name: str, phone: str = "", email: str = "", address_line: str = "",
                   city: str = "", state: str = "", postal_code: str = "", country: str = "",
                   dob: str = "", gender: str = "", notes: str = "") -> Optional[int]:
        try:
            self.cursor.execute(
                """
                INSERT INTO clients (full_name, phone, email, address_line, city, state, postal_code, country, dob, gender, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (full_name, phone, email, address_line, city, state, postal_code, country, dob, gender, notes),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"DB error adding client: {e}")
            return None

    def update_client(self, client_id: int, *, full_name: str, phone: str = "", email: str = "", address_line: str = "",
                      city: str = "", state: str = "", postal_code: str = "", country: str = "",
                      dob: str = "", gender: str = "", notes: str = "") -> bool:
        try:
            self.cursor.execute(
                """
                UPDATE clients SET full_name = ?, phone = ?, email = ?, address_line = ?, city = ?, state = ?,
                    postal_code = ?, country = ?, dob = ?, gender = ?, notes = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (full_name, phone, email, address_line, city, state, postal_code, country, dob, gender, notes, int(client_id)),
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB error updating client: {e}")
            return False

    def delete_client(self, client_id: int) -> bool:
        """Delete a client only if no invoices or payments reference it."""
        try:
            self.cursor.execute("SELECT COUNT(1) FROM invoices WHERE client_id = ?", (int(client_id),))
            inv_cnt = int(self.cursor.fetchone()[0] or 0)
            self.cursor.execute("SELECT COUNT(1) FROM client_payments WHERE client_id = ?", (int(client_id),))
            pay_cnt = int(self.cursor.fetchone()[0] or 0)
            if inv_cnt > 0 or pay_cnt > 0:
                return False
            self.cursor.execute("DELETE FROM clients WHERE id = ?", (int(client_id),))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB error deleting client: {e}")
            return False

    def list_clients(self, query: Optional[str] = None):
        try:
            if query:
                like = f"%{query}%"
                self.cursor.execute(
                    "SELECT id, full_name, phone, email, city FROM clients WHERE full_name LIKE ? OR phone LIKE ? OR email LIKE ? ORDER BY full_name ASC",
                    (like, like, like),
                )
            else:
                self.cursor.execute("SELECT id, full_name, phone, email, city FROM clients ORDER BY full_name ASC")
            return self.cursor.fetchall() or []
        except sqlite3.Error as e:
            print(f"DB error listing clients: {e}")
            return []

    def get_client(self, client_id: int):
        try:
            self.cursor.execute("SELECT * FROM clients WHERE id = ?", (int(client_id),))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"DB error getting client: {e}")
            return None

    # Payments
    def record_payment(self, client_id: int, amount: float, *, method: str = "", reference: str = "", invoice_id: Optional[int] = None) -> Optional[int]:
        try:
            self.cursor.execute(
                "INSERT INTO client_payments (client_id, invoice_id, amount, method, reference) VALUES (?, ?, ?, ?, ?)",
                (int(client_id), int(invoice_id) if invoice_id is not None else None, float(amount), method, reference),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"DB error recording payment: {e}")
            return None

    def list_client_payments(self, client_id: int):
        try:
            self.cursor.execute(
                "SELECT id, invoice_id, amount, method, reference, timestamp FROM client_payments WHERE client_id = ? ORDER BY id DESC",
                (int(client_id),),
            )
            return self.cursor.fetchall() or []
        except sqlite3.Error as e:
            print(f"DB error listing client payments: {e}")
            return []

    def list_client_invoices(self, client_id: int):
        try:
            self.cursor.execute(
                "SELECT id, invoice_number, date, total_amount FROM invoices WHERE client_id = ? ORDER BY date DESC, id DESC",
                (int(client_id),),
            )
            return self.cursor.fetchall() or []
        except sqlite3.Error as e:
            print(f"DB error listing client invoices: {e}")
            return []

    def get_client_balance(self, client_id: int) -> float:
        try:
            self.cursor.execute("SELECT COALESCE(SUM(total_amount),0) FROM invoices WHERE client_id = ?", (int(client_id),))
            inv_total = float(self.cursor.fetchone()[0] or 0.0)
            self.cursor.execute("SELECT COALESCE(SUM(amount),0) FROM client_payments WHERE client_id = ?", (int(client_id),))
            pay_total = float(self.cursor.fetchone()[0] or 0.0)
            return inv_total - pay_total
        except sqlite3.Error as e:
            print(f"DB error calculating client balance: {e}")
            return 0.0

    def get_client_recommendations(self, client_id: int, limit: int = 10):
        """Return a list of recommended products for the client based on their purchase history.
        Falls back to top items overall if client has no history. Expects invoice items_json entries with product_id or name and quantity.
        Returns list of tuples: (product_id_or_none, name, total_qty)
        """
        try:
            import json
            # Aggregate client purchases
            self.cursor.execute("SELECT items_json FROM invoices WHERE client_id = ?", (int(client_id),))
            rows = self.cursor.fetchall() or []
            counts: Dict[str, float] = {}
            for (items_json,) in rows:
                try:
                    items = json.loads(items_json) if items_json else []
                    for it in items:
                        key = str(it.get('product_id') or it.get('name') or it.get('sku') or '').strip()
                        if not key:
                            continue
                        qty = float(it.get('qty') or it.get('quantity') or 1)
                        counts[key] = counts.get(key, 0.0) + qty
                except Exception:
                    continue
            if counts:
                # Try to resolve keys to names via products if key is id
                recs = []
                for k, q in counts.items():
                    name = None
                    pid = None
                    try:
                        pid = int(k)
                        self.cursor.execute("SELECT name FROM products WHERE id = ?", (pid,))
                        row = self.cursor.fetchone()
                        name = row[0] if row else None
                    except Exception:
                        name = None
                    if not name:
                        # Use key as name fallback
                        name = k
                        pid = None
                    recs.append((pid, name, q))
                recs.sort(key=lambda t: t[2], reverse=True)
                return recs[:int(limit)]
            # Fallback: top overall items by frequency in recent invoices
            self.cursor.execute("SELECT items_json FROM invoices ORDER BY id DESC LIMIT 200")
            rows = self.cursor.fetchall() or []
            counts2: Dict[str, float] = {}
            for (items_json,) in rows:
                try:
                    items = json.loads(items_json) if items_json else []
                    for it in items:
                        key = str(it.get('product_id') or it.get('name') or it.get('sku') or '').strip()
                        if not key:
                            continue
                        qty = float(it.get('qty') or it.get('quantity') or 1)
                        counts2[key] = counts2.get(key, 0.0) + qty
                except Exception:
                    continue
            recs = []
            for k, q in counts2.items():
                name = None
                pid = None
                try:
                    pid = int(k)
                    self.cursor.execute("SELECT name FROM products WHERE id = ?", (pid,))
                    row = self.cursor.fetchone()
                    name = row[0] if row else None
                except Exception:
                    name = None
                if not name:
                    name = k
                    pid = None
                recs.append((pid, name, q))
            recs.sort(key=lambda t: t[2], reverse=True)
            return recs[:int(limit)]
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return []

    def update_location(self, location_id: int, name: str, kind: str = "") -> bool:
        """Rename or change type of a location. Returns True on success."""
        try:
            self.cursor.execute(
                "UPDATE locations SET name = ?, kind = ? WHERE id = ?",
                (name, kind, int(location_id)),
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB error updating location: {e}")
            return False

    def delete_location(self, location_id: int) -> bool:
        """Delete a location if unused. Returns False if it is referenced by movements."""
        try:
            # Prevent deleting locations referenced by stock_movements
            self.cursor.execute(
                "SELECT COUNT(1) FROM stock_movements WHERE location_id = ?",
                (int(location_id),),
            )
            cnt = int(self.cursor.fetchone()[0] or 0)
            if cnt > 0:
                return False
            self.cursor.execute("DELETE FROM locations WHERE id = ?", (int(location_id),))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"DB error deleting location: {e}")
            return False

    def get_stock(self, product_id: int, location_id: Optional[int] = None) -> int:
        try:
            if location_id is None:
                self.cursor.execute("SELECT current_stock_quantity FROM products WHERE id = ?", (product_id,))
                row = self.cursor.fetchone()
                return int(row[0]) if row and row[0] is not None else 0
            else:
                self.cursor.execute("SELECT COALESCE(SUM(quantity),0) FROM stock_movements WHERE product_id = ? AND location_id = ?", (product_id, location_id))
                row = self.cursor.fetchone()
                return int(row[0]) if row and row[0] is not None else 0
        except sqlite3.Error as e:
            print(f"DB error getting stock: {e}")
            return 0

    def transfer_stock(self, product_id: int, from_location_id: int, to_location_id: int, quantity: int) -> bool:
        if quantity <= 0:
            return False
        try:
            # Check availability at source
            available = self.get_stock(product_id, from_location_id)
            if available < quantity:
                return False
            # Out from source
            if not self.adjust_stock(product_id, -quantity, 'Transfer', None, reason='Transfer Out', location_id=from_location_id):
                return False
            # In to destination
            if not self.adjust_stock(product_id, quantity, 'Transfer', None, reason='Transfer In', location_id=to_location_id):
                return False
            return True
        except Exception as e:
            print(f"Error transferring stock: {e}")
            return False

    # -------- Movements Query --------
    def list_movements(self, product_id: int, limit: int = 100):
        try:
            self.cursor.execute(
                "SELECT timestamp, quantity, movement_type, reason, location_id, batch_id, user FROM stock_movements WHERE product_id = ? ORDER BY id DESC LIMIT ?",
                (product_id, int(limit)),
            )
            return self.cursor.fetchall() or []
        except sqlite3.Error as e:
            print(f"DB error listing movements: {e}")
            return []

    # Expiry helper
    def get_earliest_expiry(self, product_id: int):
        try:
            self.cursor.execute(
                "SELECT MIN(expiry_date) FROM batches WHERE product_id = ? AND COALESCE(blocked,0)=0 AND expiry_date IS NOT NULL",
                (product_id,),
            )
            row = self.cursor.fetchone()
            if not row or not row[0]:
                return None, None
            date_str = row[0]
            self.cursor.execute("SELECT CAST(julianday(?) - julianday(date('now')) AS INTEGER)", (date_str,))
            diff_row = self.cursor.fetchone()
            days = int(diff_row[0]) if diff_row and diff_row[0] is not None else 0
            if days < 0:
                return date_str, 'expired'
            elif days <= 7:
                return date_str, 'soon'
            else:
                return date_str, 'ok'
        except sqlite3.Error as e:
            print(f"DB error getting earliest expiry: {e}")
            return None, None

    # -------- Suppliers API (basic) --------
    def add_supplier(self, name: str, contact_info: str = "") -> Optional[int]:
        try:
            self.cursor.execute(
                "INSERT INTO suppliers (name, contact_info) VALUES (?, ?)",
                (name, contact_info),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"DB error adding supplier: {e}")
            return None

    def list_suppliers(self):
        try:
            self.cursor.execute("SELECT id, name, contact_info FROM suppliers ORDER BY name ASC")
            return self.cursor.fetchall() or []
        except sqlite3.Error as e:
            print(f"DB error listing suppliers: {e}")
            return []

    # -------- Helpers --------
    def recalc_current_stock(self, product_id: int) -> Optional[int]:
        """Recalculate and persist current stock from movements. Returns new value or None on error."""
        try:
            self.cursor.execute("SELECT COALESCE(SUM(quantity), 0) FROM stock_movements WHERE product_id = ?", (product_id,))
            total = int(self.cursor.fetchone()[0] or 0)
            self.cursor.execute("UPDATE products SET current_stock_quantity = ? WHERE id = ?", (total, product_id))
            self.conn.commit()
            return total
        except sqlite3.Error as e:
            print(f"DB error recalculating current stock: {e}")
            return None

    def get_low_stock_products(self):
        """Return products where current_stock_quantity < reorder_point."""
        try:
            self.cursor.execute(
                "SELECT id, name, current_stock_quantity, reorder_point FROM products WHERE current_stock_quantity < reorder_point"
            )
            return self.cursor.fetchall() or []
        except sqlite3.Error as e:
            print(f"DB error fetching low stock products: {e}")
            return []

    # -------- Invoices API --------
    def _next_invoice_number(self) -> str:
        import datetime
        today = datetime.datetime.now().strftime('%Y%m%d')
        prefix = f"INV-{today}-"
        try:
            self.cursor.execute("SELECT invoice_number FROM invoices WHERE invoice_number LIKE ? ORDER BY id DESC LIMIT 1", (prefix+'%',))
            row = self.cursor.fetchone()
            if row and row[0] and row[0].startswith(prefix):
                try:
                    n = int(row[0].split('-')[-1]) + 1
                except Exception:
                    n = 1
            else:
                n = 1
        except sqlite3.Error:
            n = 1
        return f"{prefix}{n:04d}"

    def create_invoice(self, items: list[dict], *, client_id: Optional[int] = None, client_name: Optional[str] = None,
                        location_id: Optional[int] = None, date: Optional[str] = None, invoice_number: Optional[str] = None) -> Optional[int]:
        """Create an invoice, persist items as JSON, and adjust stock per item at the given location.
        Each item: {product_id:int, name:str, qty:int/float, unit_price:float}
        Returns invoice id or None on failure.
        """
        import json, datetime
        if not items:
            return None
        try:
            # Validate availability
            for it in items:
                pid = int(it.get('product_id'))
                qty = float(it.get('qty') or it.get('quantity') or 0)
                if qty <= 0:
                    return None
                if location_id is not None:
                    available = self.get_stock(pid, location_id)
                    if available < qty:
                        print(f"Insufficient stock for product {pid} at location {location_id}: {available} < {qty}")
                        return None
            inv_no = invoice_number or self._next_invoice_number()
            inv_date = date or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            total = 0.0
            serializable_items = []
            for it in items:
                qty = float(it.get('qty') or it.get('quantity') or 0)
                price = float(it.get('unit_price') or it.get('price') or 0)
                line_total = qty * price
                total += line_total
                serializable_items.append({
                    'product_id': int(it.get('product_id')) if it.get('product_id') is not None else None,
                    'name': it.get('name'),
                    'qty': qty,
                    'unit_price': price,
                    'line_total': line_total,
                    'sku': it.get('sku'),
                    'barcode': it.get('barcode'),
                })
            items_json = json.dumps(serializable_items)
            # Insert invoice
            self.cursor.execute(
                "INSERT INTO invoices (invoice_number, client_name, client_id, date, total_amount, items_json) VALUES (?, ?, ?, ?, ?, ?)",
                (inv_no, client_name, int(client_id) if client_id is not None else None, inv_date, total, items_json)
            )
            inv_id = self.cursor.lastrowid
            # Adjust stock
            for it in serializable_items:
                pid = it['product_id']
                qty = float(it['qty'])
                if pid is None:
                    continue
                ok = self.adjust_stock(pid, -int(qty), movement_type='Sale', reference_id=inv_id, reason='Invoice', location_id=location_id)
                if not ok:
                    # rollback invoice insert if any adjustment fails
                    self.conn.rollback()
                    return None
            self.conn.commit()
            return inv_id
        except sqlite3.Error as e:
            print(f"DB error creating invoice: {e}")
            return None

    # -------- Business Information API --------
    def get_business_info(self):
        """Get business information. Returns a dictionary with all business info fields."""
        try:
            self.cursor.execute("""
                SELECT business_name, address_line, phone_landline, phone_mobile, fax_number, email_address,
                       bank_identity_statement, bank_name, common_company_identifier, tax_identifier,
                       trade_register_number, patente_number
                FROM business_info WHERE id = 1""")
            row = self.cursor.fetchone()
            if row:
                return {
                    'business_name': row[0],
                    'address_line': row[1],
                    'phone_landline': row[2],
                    'phone_mobile': row[3],
                    'fax_number': row[4],
                    'email_address': row[5],
                    'bank_identity_statement': row[6],
                    'bank_name': row[7],
                    'common_company_identifier': row[8],
                    'tax_identifier': row[9],
                    'trade_register_number': row[10],
                    'patente_number': row[11]
                }
            return {}
        except sqlite3.Error as e:
            print(f"DB error getting business info: {e}")
            return {}

    def update_business_info(self, business_info: dict) -> bool:
        """Update business information. Returns True on success."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM business_info WHERE id = 1")
            exists = self.cursor.fetchone()[0] > 0

            if exists:
                self.cursor.execute("""
                    UPDATE business_info 
                    SET business_name = ?, address_line = ?, phone_landline = ?, phone_mobile = ?,
                        fax_number = ?, email_address = ?, bank_identity_statement = ?, bank_name = ?,
                        common_company_identifier = ?, tax_identifier = ?, trade_register_number = ?,
                        patente_number = ?
                    WHERE id = 1""",
                    (business_info.get('business_name'),
                     business_info.get('address_line'),
                     business_info.get('phone_landline'),
                     business_info.get('phone_mobile'),
                     business_info.get('fax_number'),
                     business_info.get('email_address'),
                     business_info.get('bank_identity_statement'),
                     business_info.get('bank_name'),
                     business_info.get('common_company_identifier'),
                     business_info.get('tax_identifier'),
                     business_info.get('trade_register_number'),
                     business_info.get('patente_number')))
            else:
                self.cursor.execute("""
                    INSERT INTO business_info 
                    (id, business_name, address_line, phone_landline, phone_mobile, fax_number, email_address,
                     bank_identity_statement, bank_name, common_company_identifier, tax_identifier,
                     trade_register_number, patente_number)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (business_info.get('business_name'),
                     business_info.get('address_line'),
                     business_info.get('phone_landline'),
                     business_info.get('phone_mobile'),
                     business_info.get('fax_number'),
                     business_info.get('email_address'),
                     business_info.get('bank_identity_statement'),
                     business_info.get('bank_name'),
                     business_info.get('common_company_identifier'),
                     business_info.get('tax_identifier'),
                     business_info.get('trade_register_number'),
                     business_info.get('patente_number')))

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"DB error updating business info: {e}")
            return False

    def list_invoices(self, query: Optional[str] = None):
        try:
            if query:
                like = f"%{query}%"
                self.cursor.execute(
                    "SELECT id, invoice_number, date, client_name, client_id, total_amount FROM invoices WHERE invoice_number LIKE ? OR client_name LIKE ? ORDER BY id DESC",
                    (like, like),
                )
            else:
                self.cursor.execute("SELECT id, invoice_number, date, client_name, client_id, total_amount FROM invoices ORDER BY id DESC")
            return self.cursor.fetchall() or []
        except sqlite3.Error as e:
            print(f"DB error listing invoices: {e}")
            return []

    def get_invoice(self, invoice_id: int):
        try:
            self.cursor.execute("SELECT id, invoice_number, client_name, client_id, date, total_amount, items_json FROM invoices WHERE id = ?", (int(invoice_id),))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"DB error getting invoice: {e}")
            return None

    def get_product_by_barcode(self, barcode: str):
        """Fetch a single product by barcode. Returns tuple or None."""
        try:
            self.cursor.execute(
                "SELECT id, barcode, sku, name, description, category, current_stock_quantity, price, reorder_point, supplier_id FROM products WHERE barcode = ?",
                (barcode,),
            )
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"DB error getting product by barcode: {e}")
            return None

    def get_product(self, product_id: int):
        try:
            self.cursor.execute(
                "SELECT id, barcode, sku, name, description, category, current_stock_quantity, price, reorder_point, supplier_id FROM products WHERE id = ?",
                (product_id,),
            )
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"DB error getting product: {e}")
            return None
