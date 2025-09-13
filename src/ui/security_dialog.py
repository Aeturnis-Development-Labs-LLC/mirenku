"""
Security warning dialog for token storage
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


class SecurityWarningDialog(QDialog):
    """Dialog to warn about insecure token storage"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_accepts = False
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Security Warning - Token Storage")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Warning icon and title
        title_layout = QHBoxLayout()

        warning_label = QLabel("⚠️")
        warning_label.setStyleSheet("font-size: 48px;")
        title_layout.addWidget(warning_label)

        title = QLabel("CRITICAL SECURITY WARNING")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #d32f2f;")
        title_layout.addWidget(title)

        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Warning message
        warning_text = QTextEdit()
        warning_text.setReadOnly(True)
        warning_text.setPlainText(
            "No secure encryption method is available for storing your MyAnimeList tokens.\n\n"
            "Your authentication tokens will be stored using BASE64 ENCODING ONLY, which:\n"
            "• Is NOT encryption\n"
            "• Can be decoded by anyone with file access\n"
            "• Exposes your MAL account to potential unauthorized access\n\n"
            "RECOMMENDED ACTIONS:\n"
            "1. Cancel and install 'keyring' package: pip install keyring\n"
            "2. Or install 'cryptography' package: pip install cryptography\n"
            "3. Then restart Mirenku for secure token storage\n\n"
            "Only proceed if you understand and accept the security risk."
        )
        warning_text.setMaximumHeight(250)
        layout.addWidget(warning_text)

        # Consent checkbox
        self.consent_check = QCheckBox(
            "I understand the risk and want to proceed with INSECURE storage"
        )
        self.consent_check.setStyleSheet("color: #d32f2f;")
        self.consent_check.toggled.connect(self.on_consent_changed)
        layout.addWidget(self.consent_check)

        # Buttons
        button_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Cancel (Recommended)")
        self.cancel_btn.setDefault(True)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.proceed_btn = QPushButton("Proceed with Risk")
        self.proceed_btn.setEnabled(False)
        self.proceed_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        self.proceed_btn.clicked.connect(self.accept_risk)
        button_layout.addWidget(self.proceed_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def on_consent_changed(self, checked):
        """Handle consent checkbox change"""
        self.proceed_btn.setEnabled(checked)

    def accept_risk(self):
        """User accepts the security risk"""
        # Double confirmation
        reply = QMessageBox.critical(
            self,
            "Final Confirmation",
            "Are you ABSOLUTELY SURE you want to store your MAL tokens insecurely?\n\n"
            "This could expose your MyAnimeList account to unauthorized access.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.user_accepts = True
            logger.warning("User accepted insecure token storage risk")
            self.accept()
        else:
            logger.info("User reconsidered insecure storage on final confirmation")


class StorageUnavailableDialog(QDialog):
    """Dialog shown when no token storage is available"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Token Storage Unavailable")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QVBoxLayout()

        # Error icon and title
        title_layout = QHBoxLayout()

        error_label = QLabel("❌")
        error_label.setStyleSheet("font-size: 48px;")
        title_layout.addWidget(error_label)

        title = QLabel("Cannot Store Authentication")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #d32f2f;")
        title_layout.addWidget(title)

        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Error message
        message = QLabel(
            "Mirenku cannot store your MyAnimeList authentication tokens securely.\n\n"
            "No secure encryption method is available, and insecure storage has been disabled "
            "for your protection.\n\n"
            "To enable MAL integration, please install one of these packages:\n"
            "• keyring: pip install keyring (recommended)\n"
            "• cryptography: pip install cryptography\n\n"
            "After installation, restart Mirenku."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        # OK button
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
