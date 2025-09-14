"""
Sidebar component for AG Food application.
Contains navigation menu with icons and settings button.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QSpacerItem, QSizePolicy, QFrame
)
from PyQt6.QtCore import pyqtSignal, QSize
from PyQt6.QtGui import QIcon
from i18n.language_manager import language_manager as i18n


class SidebarWidget(QWidget):
    """Sidebar widget containing navigation with icons and settings."""
    
    # Signals
    navigation_changed = pyqtSignal(int)  # Emitted when navigation selection changes
    settings_clicked = pyqtSignal()  # Emitted when settings button is clicked
    
    # Navigation items configuration with translation keys and icon file names
    NAVIGATION_ITEMS = [
        {"key": "nav.stock_management", "icon": "stock.svg"},
        {"key": "nav.invoice_generation", "icon": "invoice.svg"},
        {"key": "nav.inventory_control", "icon": "inventory.svg"},
        {"key": "nav.order_processing", "icon": "order.svg"},
        {"key": "nav.supplier_management", "icon": "supplier.svg"},
        {"key": "nav.reports_analytics", "icon": "reports.svg"},
        {"key": "nav.quality_control", "icon": "quality.svg"}
    ]
    
    def __init__(self):
        super().__init__()
        self.icons_path = self._get_icons_path()
        self.setup_ui()
        self.connect_signals()
        
    def _get_icons_path(self) -> str:
        """Get the path to the icons directory."""
        # Get the directory where this script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to get to the project root
        project_root = os.path.dirname(current_dir)
        return os.path.join(project_root, "icons")
        
    def setup_ui(self):
        """Set up the sidebar UI components."""
        self.setFixedWidth(300)
        
        # Create main layout for the sidebar widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create frame container that will have the background styling
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebarFrame")
        
        # Create layout for the frame container
        self.sidebar_layout = QVBoxLayout(self.sidebar_frame)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)  # No margins on frame layout
        self.sidebar_layout.setSpacing(0)
        
        # Create the main navigation list
        self.navigation_list = QListWidget()
        self.navigation_list.setFrameStyle(0)  # Remove frame for cleaner look
        self.navigation_list.setContentsMargins(10, 10, 10, 0)  # Add margins to navigation list
        
        # Set icon size for navigation items (24x24 pixels)
        self.navigation_list.setIconSize(QSize(26, 26))
        
        # Add navigation items
        self.add_navigation_items()
        
        # Create settings list (separate list for settings item)
        self.settings_list = QListWidget()
        self.settings_list.setFrameStyle(0)  # Remove frame for cleaner look
        self.settings_list.setIconSize(QSize(26, 26))
        self.settings_list.setFixedHeight(50)  # Fixed height for single item
        self.settings_list.setContentsMargins(10, 0, 10, 10)  # Bottom margin for settings
        
        # Add settings item
        self.add_settings_item()
        
        # Add widgets to frame layout
        # Make navigation list expand and settings stick to bottom
        self.navigation_list.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding
        )
        self.sidebar_layout.addWidget(self.navigation_list, 1)
        self.sidebar_layout.addWidget(self.settings_list, 0)
        
        # Add frame to main layout
        main_layout.addWidget(self.sidebar_frame)
        
    def add_navigation_items(self):
        """Add navigation items with icons to the list."""
        for item_config in self.NAVIGATION_ITEMS:
            text = i18n.tr(item_config["key"])  # Translated label
            item = QListWidgetItem(text)
            
            # Try to load and set icon
            icon_path = os.path.join(self.icons_path, item_config["icon"])
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                item.setIcon(icon)
                # print(f"Loaded icon for {item_config['text']}: {icon_path}")
            else:
                print(f"Icon not found for {item_config['key']}: {icon_path}")
            
            self.navigation_list.addItem(item)
    
    def add_settings_item(self):
        """Add settings item to the settings list."""
        settings_item = QListWidgetItem(i18n.tr("nav.settings"))
        
        # Try to load settings icon
        icon_path = os.path.join(self.icons_path, "settings.svg")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            settings_item.setIcon(icon)
        else:
            print(f"Settings icon not found: {icon_path}")
        
        self.settings_list.addItem(settings_item)

    def retranslate_ui(self):
        """Retranslate all sidebar labels and items when language changes."""
        current_nav_index = self.navigation_list.currentRow()
        self.navigation_list.clear()
        self.add_navigation_items()
        if 0 <= current_nav_index < self.navigation_list.count():
            self.navigation_list.setCurrentRow(current_nav_index)

        self.settings_list.clear()
        self.add_settings_item()
    
    def connect_signals(self):
        """Connect internal signals."""
        self.navigation_list.currentRowChanged.connect(self.on_navigation_changed)
        self.settings_list.currentRowChanged.connect(self.on_settings_clicked)
    
    def on_navigation_changed(self, index):
        """Handle navigation item click."""
        if index >= 0:  # Valid selection
            # Clear settings selection and force update
            self.settings_list.clearSelection()
            self.settings_list.setCurrentRow(-1)  # Ensure no row is current
            # Emit navigation changed signal
            self.navigation_changed.emit(index)
    
    def on_settings_clicked(self, index):
        """Handle settings item click."""
        if index >= 0:  # Valid selection
            # Clear main navigation selection and force update
            self.navigation_list.clearSelection()
            self.navigation_list.setCurrentRow(-1)  # Ensure no row is current
            # Emit settings clicked signal
            self.settings_clicked.emit()
    
    def set_current_navigation(self, index):
        """Set the current navigation selection."""
        if 0 <= index < self.navigation_list.count():
            # Clear settings selection when setting main navigation
            self.settings_list.clearSelection()
            self.navigation_list.setCurrentRow(index)
    
    def clear_navigation_selection(self):
        """Clear the navigation selection."""
        self.navigation_list.clearSelection()
        
    def clear_settings_selection(self):
        """Clear the settings selection."""
        self.settings_list.clearSelection()
    
    def add_navigation_item(self, text):
        """Add a new navigation item."""
        item = QListWidgetItem(text)
        self.navigation_list.addItem(item)
    
    def get_navigation_list(self):
        """Get the navigation list widget for styling purposes."""
        return self.navigation_list
    
    def get_settings_list(self):
        """Get the settings list widget for styling purposes."""
        return self.settings_list
