"""
Theme manager module for AG Food application.
Handles all styling and theming operations including light/dark modes, QSS generation,
and custom font loading.
"""

import os
from typing import Dict, List, Optional
from PyQt6.QtGui import QFontDatabase


class ThemeManager:
    """Manages application themes, styles, and custom fonts."""
    
    # Font configuration
    FONT_FAMILY = "Alexandria"
    FONT_FALLBACKS = ["Segoe UI", "Arial", "sans-serif"]
    
    # Font files to load (will be loaded from fonts/ directory)
    FONT_FILES = [
        "Alexandria-Black.ttf",
        "Alexandria-Bold.ttf", 
        "Alexandria-ExtraBold.ttf",
        "Alexandria-ExtraLight.ttf",
        "Alexandria-Light.ttf",
        "Alexandria-Medium.ttf",
        "Alexandria-Regular.ttf",
        "Alexandria-SemiBold.ttf",
        "Alexandria-Thin.ttf"
    ]
    
    LIGHT_THEME = {
        'white': '#ffffff',
        'background': '#ffffff',
        'surface': '#f5f5f5',
        'primary': '#0078d4',
        'primary_hover': '#106ebe',
        'text': '#323130',
        'text_secondary': '#605e5c',
        'border': '#d1d1d1',
        'sidebar_bg': '#f3f2f1',
        'sidebar_hover': '#e1dfdd',
        'sidebar_selected': '#0078d4',
        'settings_bg': '#e6e6e6',
        'settings_hover': '#d4d4d4',
        'dialog_bg': '#f8f9fa',
        'dialog_border': '#ccc',
        'dialog_title': '#2c3e50',
        'input_border': '#ced4da',
        'button_primary': '#007bff',
        'button_primary_hover': '#0056b3'
    }
    
    DARK_THEME = {
        'white': '#ffffff',
        'background': '#1e1e1e',
        'surface': '#2d2d30',
        'primary': '#0078d4',
        'primary_hover': '#106ebe',
        'text': '#ffffff',
        'text_secondary': '#cccccc',
        'border': '#3c3c3c',
        'sidebar_bg': '#252526',
        'sidebar_hover': '#2a2d2e',
        'sidebar_selected': '#0078d4',
        'settings_bg': '#383838',
        'settings_hover': '#404040',
        'dialog_bg': '#2d2d30',
        'dialog_border': '#4c4c4c',
        'dialog_title': '#ffffff',
        'input_border': '#4c4c4c',
        'button_primary': '#0078d4',
        'button_primary_hover': '#106ebe'
    }
    
    def __init__(self):
        self.current_theme = 'light'
        self.font_loaded = False
        self.font_family_name = self.FONT_FAMILY
        self._load_custom_fonts()
        
    def _load_custom_fonts(self) -> None:
        """Load Alexandria font family from the fonts directory."""
        try:
            # Get the directory where this script is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to get to the project root
            project_root = os.path.dirname(current_dir)
            fonts_dir = os.path.join(project_root, "fonts")
            
            loaded_fonts: List[str] = []
            
            for font_file in self.FONT_FILES:
                font_path = os.path.join(fonts_dir, font_file)
                if os.path.exists(font_path):
                    font_id = QFontDatabase.addApplicationFont(font_path)
                    if font_id != -1:
                        font_families = QFontDatabase.applicationFontFamilies(font_id)
                        if font_families:
                            loaded_fonts.append(font_families[0])
                            # print(f"Successfully loaded font: {font_file}")
                    else:
                        print(f"Failed to load font: {font_file}")
                else:
                    print(f"Font file not found: {font_path}")
            
            if loaded_fonts:
                # Use the first loaded font family name
                self.font_family_name = loaded_fonts[0]
                self.font_loaded = True
                # print(f"Custom font family '{self.font_family_name}' loaded successfully!")
            else:
                # print("No custom fonts loaded, will use system defaults")
                self.font_loaded = False
                
        except Exception as e:
            print(f"Error loading custom fonts: {e}")
            self.font_loaded = False
    
    def get_font_family_string(self) -> str:
        """Get the complete font family string with fallbacks."""
        if self.font_loaded:
            fallbacks = ", ".join([f"'{font}'" for font in self.FONT_FALLBACKS])
            return f"'{self.font_family_name}', {fallbacks}"
        else:
            fallbacks = ", ".join([f"'{font}'" for font in self.FONT_FALLBACKS])
            return fallbacks
        
    def get_theme_colors(self, theme_name='light'):
        """Get color palette for specified theme."""
        return self.LIGHT_THEME if theme_name == 'light' else self.DARK_THEME
    def get_main_stylesheet(self, theme_name='light'):
        """Generate main application stylesheet with custom font."""
        colors = self.get_theme_colors(theme_name)
        font_family = self.get_font_family_string()
        
        return f"""
        QMainWindow {{
            background-color: {colors['background']};
            color: {colors['text']};
            font-family: {font_family};
        }}
        
        QWidget {{
            background-color: {colors['background']};
            color: {colors['text']};
            font-family: {font_family};
        }}
        
        QLabel {{
            color: {colors['text']};
            font-size: 14px;
            font-family: {font_family};
        }}

        /* ---------------- Settings Page ---------------- */
        QWidget#settingsRoot {{
            background-color: {colors['surface']};
        }}

        /* Tabs */
        QWidget#settingsRoot QTabWidget::pane {{
            border: 1px solid {colors['border']};
            border-radius: 8px;
            background: {colors['background']};
            margin-top: 10px;
        }}

        QWidget#settingsRoot QTabBar::tab {{
            background: transparent;
            color: {colors['text']};
            padding: 8px 14px;
            margin-right: 6px;
            border: 1px solid transparent;
            border-bottom: 2px solid transparent;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: 500;
        }}

        QWidget#settingsRoot QTabBar::tab:selected {{
            background: {colors['background']};
            border-color: {colors['border']};
            border-bottom: 2px solid {colors['primary']};
        }}

        QWidget#settingsRoot QTabBar::tab:hover:!selected {{
            background: {colors['settings_hover']};
        }}

        /* Labels inside settings */
        QWidget#settingsRoot QLabel {{
            color: {colors['text_secondary']};
            font-size: 14px;
            font-weight: 600;
        }}

        /* Dropdowns */
        QWidget#settingsRoot QComboBox {{
            background: {colors['background']};
            color: {colors['text']};
            border: 1px solid {colors['input_border']};
            border-radius: 6px;
            padding: 6px 10px;
            min-width: 200px;
        }}

        QWidget#settingsRoot QComboBox:hover {{
            border-color: {colors['primary']};
        }}

        QWidget#settingsRoot QComboBox:focus {{
            border-color: {colors['primary']};
        }}

        QWidget#settingsRoot QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border-left: 1px solid {colors['border']};
        }}

        QWidget#settingsRoot QComboBox QAbstractItemView {{
            background: {colors['surface']};
            color: {colors['text']};
            border: 1px solid {colors['border']};
            selection-background-color: {colors['primary']};
            selection-color: white;
        }}
        """
        
    def get_sidebar_stylesheet(self, theme_name='light'):
        """Generate sidebar-specific stylesheet with custom font."""
        colors = self.get_theme_colors(theme_name)
        font_family = self.get_font_family_string()
        
        return f"""
        QFrame#sidebarFrame {{
            background-color: {colors['sidebar_bg']};
            border-right: 2px solid {colors['border']};
        }}
        
        QListWidget {{
            background-color: transparent;
            border: none;
            font-size: 18px;
            font-family: {font_family};
            color: {colors['text']};
            outline: none;
        }}
        
        QListWidget::item {{
            padding: 10px 5px;
            border-bottom: 1px solid {colors['border']};
            background-color: transparent;
            font-family: {font_family};
        }}
        
        QListWidget::item:selected {{
            background-color: {colors['sidebar_selected']};
            color: white;

        }}
        
        QListWidget::item:hover:!selected {{
            background-color: {colors['sidebar_hover']};

        }}
        
        QListWidget::item:last {{
            border-bottom: none;
        }}
        
        /* Icon spacing and size */
        QListWidget QListWidgetItem {{
            padding-left: 44px; /* Space for icon */
        }}
        """
        
    def get_settings_button_stylesheet(self, theme_name='light'):
        """Generate settings button stylesheet with custom font."""
        colors = self.get_theme_colors(theme_name)
        font_family = self.get_font_family_string()
        
        return f"""
        QPushButton {{
            background-color: {colors['settings_bg']};
            border: 1px solid {colors['border']};

            padding: 10px;
            font-size: 13px;
            font-family: {font_family};
            color: {colors['text']};
            text-align: left;
            font-weight: 500;
        }}
        
        QPushButton:hover {{
            background-color: {colors['settings_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {colors['primary']};
            color: white;
        }}
        """
        
    def get_header_stylesheet(self, theme_name='light'):
        """Generate header-specific stylesheet with custom font."""
        colors = self.get_theme_colors(theme_name)
        font_family = self.get_font_family_string()
        
        return f"""
        QWidget#header {{
            background-color: transparent;
            padding: 0px;
        }}
        
        QWidget#headerContainer {{
            background-color: {colors['primary']};
            border: none;
            border-radius: 0px;
        }}
        
        QLabel#appName {{
            color: white;
            background-color: transparent;
            font-size: 22px;
            font-family: {font_family};
            font-weight: bold;
            padding: 0px;
        }}
        
        QLabel#userName {{
            color: {colors['white']};
            background-color: transparent;
            font-size: 14px;
            font-family: {font_family};
            padding: 0px;
            font-weight: 500;
        }}
        
        QLabel#adminIcon {{
            background-color: transparent;
            padding: 0px;
            margin: 0px;
        }}
        """
        
    def get_login_dialog_stylesheet(self, theme_name='light'):
        """Generate login dialog-specific stylesheet with custom font."""
        colors = self.get_theme_colors(theme_name)
        font_family = self.get_font_family_string()
        
        return f"""
        QDialog {{
            background-color: {colors['dialog_bg']};
            border: 2px solid {colors['dialog_border']};
            font-family: {font_family};
        }}
        
        QLabel {{
            font-family: {font_family};
            font-size: 16px;
            color: {colors['text']};
        }}
        
        QLineEdit {{
            border: 1px solid {colors['input_border']};
            padding: 8px;
            font-size: 14px;
            font-family: {font_family};
            background-color: {colors['background']};
            color: {colors['text']};
        }}
        
        QLineEdit:focus {{
            border: 2px solid {colors['primary']};
        }}
        
        QPushButton {{
            background-color: {colors['button_primary']};
            color: white;
            border: none;
            padding: 10px;
            font-weight: bold;
            font-size: 16px;
            font-family: {font_family};
        }}
        
        QPushButton:hover {{
            background-color: {colors['button_primary_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {colors['primary_hover']};
        }}
        
        #title_label {{
            font-size: 24px;
            font-weight: bold;
            color: {colors['dialog_title']};
            margin-bottom: 20px;
            text-align: center;
            font-family: {font_family};
        }}
        """
