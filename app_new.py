"""
AG Food - Stock & Invoice Manager
Main application entry point.

This application provides stock management and invoice generation functionality
for AG Food business operations.
"""

import sys
from PyQt6.QtWidgets import QApplication

from database.manager import DatabaseManager
from ui.main_window import MainAppWindow


def main():
    """Main application entry point."""
    # Create the application
    app = QApplication(sys.argv)
    
    # Initialize the database manager
    db_manager = DatabaseManager()

    # Create the main window
    main_window = MainAppWindow(db_manager)

    # Connect database signals to main window
    db_manager.database_ready.connect(main_window.show)
    db_manager.database_error.connect(main_window.show_db_error)

    # Start the database connection process
    db_manager.connect_db()

    # Start the application event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()