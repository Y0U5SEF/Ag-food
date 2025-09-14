"""
Main window component for AG Food application.
Coordinates header, sidebar, and content areas.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QLabel, QMessageBox
)

from .header import HeaderWidget
from .sidebar import SidebarWidget
from styles.theme_manager import ThemeManager


class MainAppWindow(QMainWindow):
    """The main application window, which contains the complete UI."""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.theme_manager = ThemeManager()
        self.setup_window()
        self.setup_ui()
        self.connect_signals()
        self.apply_theme()
        
    def setup_window(self):
        """Set up basic window properties."""
        self.setWindowTitle("AG Food - Stock & Invoice Manager")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(600, 400)
        
    def setup_ui(self):
        """Set up the main UI structure."""
        # Set up central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header
        self.header = HeaderWidget()
        
        # Create content area below header
        self.content_area = QWidget()
        self.content_layout = QHBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = SidebarWidget()
        
        # Create main content stack
        self.content_stack = QStackedWidget()
        
        # Create content widgets
        self.setup_content_widgets()
        
        # Assemble layout
        self.content_layout.addWidget(self.sidebar)
        self.content_layout.addWidget(self.content_stack)
        
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_area)
        
        # Set initial navigation
        self.sidebar.set_current_navigation(0)
        
    def setup_content_widgets(self):
        """Set up the content widgets for each section."""
        # Stock Management content
        self.stock_widget = QWidget()
        stock_layout = QVBoxLayout(self.stock_widget)
        stock_layout.addWidget(QLabel("Stock Management UI will be here."))
        
        # Invoice Generation content
        self.invoice_widget = QWidget()
        invoice_layout = QVBoxLayout(self.invoice_widget)
        invoice_layout.addWidget(QLabel("Invoice Generation UI will be here."))
        
        # Settings content
        self.settings_widget = QWidget()
        settings_layout = QVBoxLayout(self.settings_widget)
        settings_layout.addWidget(QLabel("Settings UI will be here."))
        settings_layout.addWidget(QLabel("- Theme selection (Light/Dark)"))
        settings_layout.addWidget(QLabel("- Language selection (English/Arabic)"))
        settings_layout.addWidget(QLabel("- RTL layout support"))
        
        # Add to stack
        self.content_stack.addWidget(self.stock_widget)
        self.content_stack.addWidget(self.invoice_widget)
        self.content_stack.addWidget(self.settings_widget)
        
    def connect_signals(self):
        """Connect signals between components."""
        # Sidebar signals
        self.sidebar.navigation_changed.connect(self.switch_content)
        self.sidebar.settings_clicked.connect(self.show_settings)
        
    def switch_content(self, index):
        """Switch the main content area based on navigation selection."""
        if index >= 0:  # Valid selection
            self.content_stack.setCurrentIndex(index)
            
    def show_settings(self):
        """Show the settings panel when settings button is clicked."""
        # Clear sidebar selection to indicate we're in settings
        self.sidebar.clear_navigation_selection()
        # Switch to settings content (index 2)
        self.content_stack.setCurrentIndex(2)
        
    def apply_theme(self, theme_name='light'):
        """Apply the specified theme to the entire application."""
        self.theme_manager.current_theme = theme_name
        
        # Apply main application stylesheet
        self.setStyleSheet(self.theme_manager.get_main_stylesheet(theme_name))
        
        # Apply component-specific stylesheets
        self.header.setStyleSheet(self.theme_manager.get_header_stylesheet(theme_name))
        self.sidebar.get_navigation_list().setStyleSheet(
            self.theme_manager.get_sidebar_stylesheet(theme_name)
        )
        self.sidebar.get_settings_button().setStyleSheet(
            self.theme_manager.get_settings_button_stylesheet(theme_name)
        )
        
    def toggle_theme(self):
        """Toggle between light and dark theme."""
        new_theme = 'dark' if self.theme_manager.current_theme == 'light' else 'light'
        self.apply_theme(new_theme)
        
    def show_db_error(self, message):
        """Display a message box with a database connection error."""
        QMessageBox.critical(self, "Database Error", message)
        
    def update_username(self, username):
        """Update the username displayed in the header."""
        self.header.update_username(username)