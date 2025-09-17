"""
Main window component for AG Food application.
Coordinates header, sidebar, and content areas.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QMessageBox, QTabWidget, QComboBox, QFormLayout,
    QGridLayout, QToolButton, QLineEdit, QSizePolicy, QPushButton, QSpacerItem
)
from PyQt6.QtWidgets import QStyle
from PyQt6.QtCore import QSize
from typing import Optional
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from .header import HeaderWidget
from .sidebar import SidebarWidget
from styles.theme_manager import ThemeManager
from .inventory import InventoryControlWidget
from .invoice import InvoiceWidget
from i18n.language_manager import language_manager as i18n
from config.app_config import AppConfig
from .stock import StockManagementWidget
from .clients import ClientsManagementWidget


class MainAppWindow(QMainWindow):
    """The main application window, which contains the complete UI."""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.theme_manager = ThemeManager()
        self.app_config = AppConfig()
        self.setup_window()
        self.setup_ui()
        self.connect_signals()
        self.apply_theme()
        # Apply language after UI is constructed
        self.apply_language()
        
    def setup_window(self):
        """Set up basic window properties."""
        # Title will be set by language application
        self.setWindowTitle(i18n.tr('app.window_title'))
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
        self.stock_widget = StockManagementWidget(self.db_manager)
        
        # Invoice Generation content
        self.invoice_widget = InvoiceWidget(self.db_manager, stock_widget=self.stock_widget)
        
        # Settings content with tabs (General tab -> Language)
        self.settings_widget = QWidget()
        self.settings_widget.setObjectName("settingsRoot")
        settings_layout = QVBoxLayout(self.settings_widget)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setSpacing(12)

        self.settings_tabs = QTabWidget()
        self.settings_tabs.setObjectName("settingsTabs")
        self.general_tab = QWidget()
        general_form = QFormLayout(self.general_tab)
        general_form.setContentsMargins(12, 12, 12, 12)
        general_form.setHorizontalSpacing(16)
        general_form.setVerticalSpacing(14)
        self.language_label = QLabel(i18n.tr('settings.language.label'))
        self.language_combo = QComboBox()
        # Populate with visible names, store lang code in itemData
        for code, label in i18n.SUPPORTED.items():
            self.language_combo.addItem(label, userData=code)
        # Set current language
        current_lang = i18n.get_language()
        idx = self.language_combo.findData(current_lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)

        general_form.addRow(self.language_label, self.language_combo)
        self.settings_tabs.addTab(self.general_tab, i18n.tr('settings.tab.general'))
        
        # Business Information tab
        self.business_tab = QWidget()
        business_form = QFormLayout(self.business_tab)
        business_form.setContentsMargins(12, 12, 12, 12)
        business_form.setHorizontalSpacing(16)
        business_form.setVerticalSpacing(14)

        self.business_name_edit = QLineEdit()
        self.business_address_edit = QLineEdit()
        self.business_phone_landline_edit = QLineEdit()
        self.business_phone_mobile_edit = QLineEdit()
        self.business_fax_edit = QLineEdit()
        self.business_email_edit = QLineEdit()
        self.bank_identity_statement_edit = QLineEdit()
        self.bank_name_edit = QLineEdit()
        self.common_company_identifier_edit = QLineEdit()
        self.tax_identifier_edit = QLineEdit()
        self.trade_register_number_edit = QLineEdit()
        self.business_patente_edit = QLineEdit()

        business_form.addRow(QLabel(i18n.tr('business.name')), self.business_name_edit)
        business_form.addRow(QLabel(i18n.tr('business.address')), self.business_address_edit)
        business_form.addRow(QLabel(i18n.tr('business.phone_landline')), self.business_phone_landline_edit)
        business_form.addRow(QLabel(i18n.tr('business.phone_mobile')), self.business_phone_mobile_edit)
        business_form.addRow(QLabel(i18n.tr('business.fax')), self.business_fax_edit)
        business_form.addRow(QLabel(i18n.tr('business.email')), self.business_email_edit)
        business_form.addRow(QLabel(i18n.tr('business.bank_identity')), self.bank_identity_statement_edit)
        business_form.addRow(QLabel(i18n.tr('business.bank_name')), self.bank_name_edit)
        business_form.addRow(QLabel(i18n.tr('business.company_id')), self.common_company_identifier_edit)
        business_form.addRow(QLabel(i18n.tr('business.tax_id')), self.tax_identifier_edit)
        business_form.addRow(QLabel(i18n.tr('business.trade_register')), self.trade_register_number_edit)
        business_form.addRow(QLabel(i18n.tr('business.patente')), self.business_patente_edit)

        # Add a vertical spacer to push the button container to the bottom.
        business_form.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Create a new layout for the button to control its alignment.
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # Add a spacer to push the button to the right.
        
        # Add Save button.
        self.save_business_info_button = QPushButton(i18n.tr('settings.save_business_info'))
        self.save_business_info_button.setStyleSheet(self.theme_manager.get_global_button_stylesheet())
        self.save_business_info_button.clicked.connect(self.save_business_info)
        
        button_layout.addWidget(self.save_business_info_button)
        
        # Add the button layout to a new row in the form.
        business_form.addRow(button_layout)
        
        self.settings_tabs.addTab(self.business_tab, i18n.tr('business.name'))
        
        # Note: Not loading business info here because database might not be ready yet
        # Load existing business info will be called when database is ready
        
        # Clients management content
        self.clients_widget = ClientsManagementWidget(self.db_manager)

        # Inventory Control content (Manage Locations)
        self.inventory_widget = InventoryControlWidget(self.db_manager, stock_widget=self.stock_widget)

        settings_layout.addWidget(self.settings_tabs)
        
        # Add to stack in same order as sidebar NAVIGATION_ITEMS
        # 0: Stock, 1: Invoice, 2: Clients, 3: Inventory Control, ...
        self.content_stack.addWidget(self.stock_widget)        # index 0
        self.content_stack.addWidget(self.invoice_widget)      # index 1
        self.content_stack.addWidget(self.clients_widget)      # index 2
        self.content_stack.addWidget(self.inventory_widget)    # index 3
        self.content_stack.addWidget(self.settings_widget)     # index 4 (settings accessed from gear)
        
    def connect_signals(self):
        """Connect signals between components."""
        # Sidebar signals
        self.sidebar.navigation_changed.connect(self.switch_content)
        self.sidebar.settings_clicked.connect(self.show_settings)
        # Settings signals
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        
        # Save business info when switching away from settings
        self.content_stack.currentChanged.connect(self.on_content_changed)
        
    def switch_content(self, index):
        """Switch the main content area based on navigation selection."""
        if index >= 0:  # Valid selection
            self.content_stack.setCurrentIndex(index)
            # Ensure inventory view refreshes when navigated to
            try:
                inv_index = 3
                if index == inv_index and hasattr(self, 'inventory_widget'):
                    self.inventory_widget.refresh()
            except Exception:
                pass
            
    def show_settings(self):
        """Show the settings panel when settings button is clicked."""
        # Switch to settings content (index 4)
        self.content_stack.setCurrentIndex(4)
        # Reload business info when showing settings
        self.load_business_info()
        
    def load_business_info(self):
        """Load business information from database into the form fields."""
        try:
            business_info = self.db_manager.get_business_info()
            if business_info:
                self.business_name_edit.setText(business_info.get('business_name', ''))
                self.business_address_edit.setText(business_info.get('address_line', ''))
                self.business_phone_landline_edit.setText(business_info.get('phone_landline', ''))
                self.business_phone_mobile_edit.setText(business_info.get('phone_mobile', ''))
                self.business_fax_edit.setText(business_info.get('fax_number', ''))
                self.business_email_edit.setText(business_info.get('email_address', ''))
                self.bank_identity_statement_edit.setText(business_info.get('bank_identity_statement', ''))
                self.bank_name_edit.setText(business_info.get('bank_name', ''))
                self.common_company_identifier_edit.setText(business_info.get('common_company_identifier', ''))
                self.tax_identifier_edit.setText(business_info.get('tax_identifier', ''))
                self.trade_register_number_edit.setText(business_info.get('trade_register_number', ''))
                self.business_patente_edit.setText(business_info.get('patente_number', ''))
        except Exception as e:
            print(f"Error loading business info: {e}")
            
    def save_business_info(self):
        """Save business information from form fields to database."""
        try:
            business_info = {
                'business_name': self.business_name_edit.text().strip(),
                'address_line': self.business_address_edit.text().strip(),
                'phone_landline': self.business_phone_landline_edit.text().strip(),
                'phone_mobile': self.business_phone_mobile_edit.text().strip(),
                'fax_number': self.business_fax_edit.text().strip(),
                'email_address': self.business_email_edit.text().strip(),
                'bank_identity_statement': self.bank_identity_statement_edit.text().strip(),
                'bank_name': self.bank_name_edit.text().strip(),
                'common_company_identifier': self.common_company_identifier_edit.text().strip(),
                'tax_identifier': self.tax_identifier_edit.text().strip(),
                'trade_register_number': self.trade_register_number_edit.text().strip(),
                'patente_number': self.business_patente_edit.text().strip()
            }
            success = self.db_manager.update_business_info(business_info)
            if not success:
                QMessageBox.warning(self, "Save Error", "Failed to save business information.")
        except Exception as e:
            print(f"Error saving business info: {e}")
            QMessageBox.warning(self, "Save Error", f"Error saving business information: {e}")
            
    def on_content_changed(self, index):
        """Called when content stack changes. Save business info if moving away from settings."""
        settings_index = 4  # Index of settings tab
        if self.content_stack.currentIndex() != settings_index and index != settings_index:
            # We're moving away from settings, save business info
            self.save_business_info()
            
    def closeEvent(self, a0):
        """Override close event to save business information before closing."""
        self.save_business_info()
        super().closeEvent(a0)
        
    def apply_theme(self, theme_name='light'):
        """Apply the specified theme to the entire application."""
        self.theme_manager.current_theme = theme_name
        
        # Apply main application stylesheet
        self.setStyleSheet(self.theme_manager.get_main_stylesheet(theme_name))
        
        # Apply component-specific stylesheets
        self.header.setStyleSheet(self.theme_manager.get_header_stylesheet(theme_name))
        self.sidebar.sidebar_frame.setStyleSheet(
            self.theme_manager.get_sidebar_stylesheet(theme_name)
        )
        
    def toggle_theme(self):
        """Toggle between light and dark theme."""
        new_theme = 'dark' if self.theme_manager.current_theme == 'light' else 'light'
        self.apply_theme(new_theme)
        
    def set_login_dialog_theme(self, login_dialog):
        """Apply current theme to login dialog."""
        login_dialog.set_theme(self.theme_manager.current_theme)
        
    def show_db_error(self, message):
        """Display a message box with a database connection error."""
        QMessageBox.critical(self, "Database Error", message)
        
    def update_username(self, user_data):
        """Update the username displayed in the header with user's full name."""
        if isinstance(user_data, dict) and 'full_name' in user_data:
            full_name = user_data['full_name']
            self.header.update_username(full_name)
            print(f"Updated header with user: {full_name}")
        else:
            # Fallback for backward compatibility
            username = user_data if isinstance(user_data, str) else "Unknown User"
            self.header.update_username(username)

    # --- Language/i18n ---
    def on_language_changed(self):
        code = self.language_combo.currentData()
        if not code:
            return
        i18n.set_language(code)
        # Update layout direction globally
        app = QApplication.instance()
        if app is not None:
            app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if i18n.is_rtl() else Qt.LayoutDirection.LeftToRight)
        self.apply_language()
        # Persist language choice
        try:
            self.app_config.set_language(code)
            self.app_config.save()
        except Exception:
            pass

    def apply_language(self):
        """Apply current language to all visible UI texts."""
        # Window title
        self.setWindowTitle(i18n.tr('app.window_title'))

        # Sidebar items
        self.sidebar.retranslate_ui()

        # Stock management UI
        if hasattr(self, 'stock_widget'):
            self.stock_widget.retranslate_ui()
        # Clients management UI
        if hasattr(self, 'clients_widget'):
            self.clients_widget.retranslate_ui()

        # Settings tab texts
        tab_index = self.settings_tabs.indexOf(self.general_tab)
        if tab_index != -1:
            self.settings_tabs.setTabText(tab_index, i18n.tr('settings.tab.general'))
        
        # Business info tab text
        business_tab_index = self.settings_tabs.indexOf(self.business_tab)
        if business_tab_index != -1:
            self.settings_tabs.setTabText(business_tab_index, i18n.tr('business.name'))
            
        self.language_label.setText(i18n.tr('settings.language.label'))

        # Content placeholders
        # These are simple labels we added; find and set if present
        # Stock widget manages its own labels; nothing to retranslate here for now
        if isinstance(self.invoice_widget.layout().itemAt(0).widget(), QLabel):
            self.invoice_widget.layout().itemAt(0).widget().setText(i18n.tr('content.invoice.placeholder'))
        # Settings page placeholder isn't used anymore (tabs), so nothing to update here
