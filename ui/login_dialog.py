from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QMessageBox, QFrame
)
from PyQt6.QtCore import pyqtSignal
from styles.theme_manager import ThemeManager

class LoginDialog(QDialog):
    """A modal dialog for user login."""
    login_successful = pyqtSignal(dict)  # Changed to pass user data

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.theme_manager = ThemeManager()
        self.setWindowTitle("Login")
        self.setFixedSize(400, 300)
        self.apply_theme()
        self.setup_ui()
    
    def apply_theme(self, theme_name='light'):
        """Apply theme styles to the login dialog."""
        self.setStyleSheet(self.theme_manager.get_login_dialog_stylesheet(theme_name))
        
    def set_theme(self, theme_name):
        """Set the theme for the login dialog."""
        self.theme_manager.current_theme = theme_name
        self.apply_theme(theme_name)
    
    def setup_ui(self):
        """Set up the UI for the login form."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)

        title_label = QLabel("AG Food Login")
        title_label.setObjectName("title_label")
        main_layout.addWidget(title_label)

        form_frame = QFrame()
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setText("admin")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setText("admin")
        
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)

        self.login_button = QPushButton("Login")
        
        main_layout.addWidget(form_frame)
        main_layout.addWidget(self.login_button)
        
        self.login_button.clicked.connect(self.handle_login)
        # Allow pressing Enter to submit
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)

    def handle_login(self):
        """Handle the login button click."""
        username = self.username_input.text()
        password = self.password_input.text()
        
        user_data = self.db_manager.authenticate_user(username, password)
        if user_data:  # user_data is a dict if successful, False if failed
            self.login_successful.emit(user_data)
            self.accept()  # Close the dialog
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password. Please try again.")
            self.password_input.clear()
            self.username_input.clear()
            self.username_input.setFocus()
