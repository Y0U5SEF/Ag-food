"""
Sidebar component for AG Food application.
Contains navigation menu with icons and settings button.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, QSize
from PyQt6.QtGui import QIcon


class SidebarWidget(QWidget):
    """Sidebar widget containing navigation with icons and settings."""
    
    # Signals
    navigation_changed = pyqtSignal(int)  # Emitted when navigation selection changes
    settings_clicked = pyqtSignal()  # Emitted when settings button is clicked
    
    # Navigation items configuration with icon file names
    NAVIGATION_ITEMS = [
        {"text": "Stock Management", "icon": "stock.svg"},
        {"text": "Invoice Generation", "icon": "invoice.svg"}
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
        
        # Create main layout
        self.sidebar_layout = QVBoxLayout(self)
        self.sidebar_layout.setContentsMargins(10, 10, 10, 10)
        self.sidebar_layout.setSpacing(0)
        
        # Create the main navigation list
        self.navigation_list = QListWidget()
        self.navigation_list.setFrameStyle(0)  # Remove frame for cleaner look
        
        # Set icon size for navigation items (24x24 pixels)
        self.navigation_list.setIconSize(QSize(24, 24))
        
        # Add navigation items
        self.add_navigation_items()
        
        # Add spacer to push settings button to bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        
        # Create settings button
        self.settings_button = QPushButton("⚙️ Settings")
        
        # Add widgets to layout
        self.sidebar_layout.addWidget(self.navigation_list)
        self.sidebar_layout.addItem(spacer)
        self.sidebar_layout.addWidget(self.settings_button)
        
    def add_navigation_items(self):
        """Add navigation items with icons to the list."""
        for item_config in self.NAVIGATION_ITEMS:
            item = QListWidgetItem(item_config["text"])
            
            # Try to load and set icon
            icon_path = os.path.join(self.icons_path, item_config["icon"])
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                item.setIcon(icon)
                print(f"Loaded icon for {item_config['text']}: {icon_path}")
            else:
                print(f"Icon not found for {item_config['text']}: {icon_path}")
            
            self.navigation_list.addItem(item)
    
    def connect_signals(self):
        """Connect internal signals."""
        self.navigation_list.currentRowChanged.connect(self.navigation_changed.emit)
        self.settings_button.clicked.connect(self.settings_clicked.emit)
    
    def set_current_navigation(self, index):
        """Set the current navigation selection."""
        if 0 <= index < self.navigation_list.count():
            self.navigation_list.setCurrentRow(index)
    
    def clear_navigation_selection(self):
        """Clear the navigation selection."""
        self.navigation_list.clearSelection()
    
    def add_navigation_item(self, text):
        """Add a new navigation item."""
        item = QListWidgetItem(text)
        self.navigation_list.addItem(item)
    
    def get_navigation_list(self):
        """Get the navigation list widget for styling purposes."""
        return self.navigation_list
    
    def get_settings_button(self):
        """Get the settings button for styling purposes."""
        return self.settings_button