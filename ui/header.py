"""
Header component for AG Food application.
Contains app branding and user information display with admin icon.
"""

import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap


class HeaderWidget(QWidget):
    """Header widget containing app name and user information."""
    
    def __init__(self, app_name="AG Food", username="John Doe"):
        super().__init__()
        self.app_name = app_name
        self.username = username
        self.icons_path = self._get_icons_path()
        self.setup_ui()
        
    def _get_icons_path(self) -> str:
        """Get the path to the icons directory."""
        # Get the directory where this script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to get to the project root
        project_root = os.path.dirname(current_dir)
        return os.path.join(project_root, "icons")
        
    def setup_ui(self):
        """Set up the header UI components."""
        self.setObjectName("header")
        self.setFixedHeight(80)
        
        # Create main layout for the header widget
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create container widget that will have the background styling
        self.container_widget = QWidget()
        self.container_widget.setObjectName("headerContainer")
        
        # Create layout for the container
        self.header_layout = QHBoxLayout(self.container_widget)
        self.header_layout.setContentsMargins(16, 12, 16, 12)  # Add padding inside container
        self.header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Center vertically
        
        # App name on the left
        self.app_name_label = QLabel(self.app_name)
        self.app_name_label.setObjectName("appName")
        self.app_name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Create user info container (username + admin icon)
        self.user_info_widget = QWidget()
        self.user_info_widget.setStyleSheet("background:transparent;")
        self.user_info_layout = QHBoxLayout(self.user_info_widget)
        self.user_info_layout.setContentsMargins(0, 0, 0, 0)
        self.user_info_layout.setSpacing(8)  # Space between username and icon
        self.user_info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Username label
        self.user_name_label = QLabel(self.username)
        self.user_name_label.setObjectName("userName")
        self.user_name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Admin icon label
        self.admin_icon_label = QLabel()
        self.admin_icon_label.setObjectName("adminIcon")
        self.admin_icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.load_admin_icon()
        
        # Add username and icon to user info layout
        self.user_info_layout.addWidget(self.admin_icon_label)
        self.user_info_layout.addWidget(self.user_name_label)
        
        
        # Add to container layout
        self.header_layout.addWidget(self.app_name_label)
        self.header_layout.addStretch()  # Push user info to the right
        self.header_layout.addWidget(self.user_info_widget)
        
        # Add container to main layout
        main_layout.addWidget(self.container_widget)
    
    def load_admin_icon(self):
        """Load and set the admin icon."""
        icon_path = os.path.join(self.icons_path, "admin.svg")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            # Scale the icon to appropriate size (24x24 to match the header height proportionally)
            scaled_pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.admin_icon_label.setPixmap(scaled_pixmap)
            print(f"Admin icon loaded: {icon_path}")
        else:
            # If icon not found, hide the label
            self.admin_icon_label.hide()
            print(f"Admin icon not found: {icon_path}")
    
    def update_username(self, username):
        """Update the displayed username."""
        self.username = username
        self.user_name_label.setText(username)
    
    def update_app_name(self, app_name):
        """Update the displayed app name."""
        self.app_name = app_name
        self.app_name_label.setText(app_name)