"""
Header component for AG Food application.
Contains app branding and user information display.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt


class HeaderWidget(QWidget):
    """Header widget containing app name and user information."""
    
    def __init__(self, app_name="AG Food", username="John Doe"):
        super().__init__()
        self.app_name = app_name
        self.username = username
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the header UI components."""
        self.setObjectName("header")
        self.setFixedHeight(50)
        
        # Create layout
        self.header_layout = QHBoxLayout(self)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        
        # App name on the left
        self.app_name_label = QLabel(self.app_name)
        self.app_name_label.setObjectName("appName")
        
        # Username on the right (dummy for now)
        self.user_name_label = QLabel(self.username)
        self.user_name_label.setObjectName("userName")
        self.user_name_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Add to layout
        self.header_layout.addWidget(self.app_name_label)
        self.header_layout.addStretch()  # Push username to the right
        self.header_layout.addWidget(self.user_name_label)
    
    def update_username(self, username):
        """Update the displayed username."""
        self.username = username
        self.user_name_label.setText(username)
    
    def update_app_name(self, app_name):
        """Update the displayed app name."""
        self.app_name = app_name
        self.app_name_label.setText(app_name)