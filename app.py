"""
AG Food - Stock & Invoice Manager
Main application entry point.

This application provides stock management and invoice generation functionality
for AG Food business operations.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from ui.main_window import MainAppWindow
from ui.login_dialog import LoginDialog
from database.manager import DatabaseManager
from config.app_config import AppConfig
from i18n.language_manager import language_manager as i18n

# --- DEVELOPMENT FLAG ---
# Set to True to skip the login screen during development
DISABLE_LOGIN = True

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Load persisted app config (e.g., language) and apply upfront
    app_config = AppConfig()
    i18n.set_language(app_config.get_language())
    # Apply initial layout direction based on language (RTL for Arabic)
    app.setLayoutDirection(
        Qt.LayoutDirection.RightToLeft if i18n.is_rtl() else Qt.LayoutDirection.LeftToRight
    )
    
    # Initialize the database manager
    db_manager = DatabaseManager()
    
    # We will connect to the database first, and then handle the UI flow
    # based on the connection status and login flag.
    
    def on_db_ready():
        """Handles the UI flow after the database is successfully connected."""
        # Load business info now that database is ready
        main_window.load_business_info()
        
        if DISABLE_LOGIN:
            print("Login disabled. Showing main window directly.")
            main_window.showMaximized()
        else:
            login_dialog.show()

    def on_db_error(message):
        """Displays a message and exits the application on database error."""
        QMessageBox.critical(None, "Application Error", f"Failed to initialize the database:\n{message}")
        sys.exit(1)

    # Create the main application window (but don't show it yet)
    main_window = MainAppWindow(db_manager)
    # Create the login dialog (but don't show it yet)
    login_dialog = LoginDialog(db_manager)
    
    # Apply consistent theme to login dialog
    login_dialog.set_theme(main_window.theme_manager.current_theme)

    # Connect signals
    db_manager.database_ready.connect(on_db_ready)
    db_manager.database_error.connect(on_db_error)
    login_dialog.login_successful.connect(main_window.update_username)
    login_dialog.login_successful.connect(lambda user_data: main_window.showMaximized())
    # Track current user for audit trail
    def _set_db_user(user_data):
        try:
            if isinstance(user_data, dict) and 'full_name' in user_data:
                db_manager.current_user = user_data['full_name']
            elif isinstance(user_data, dict) and 'username' in user_data:
                db_manager.current_user = user_data['username']
            elif isinstance(user_data, str):
                db_manager.current_user = user_data
        except Exception:
            pass
    login_dialog.login_successful.connect(_set_db_user)

    # Start the database connection process
    db_manager.connect_db()

    # The application event loop will start here
    sys.exit(app.exec())