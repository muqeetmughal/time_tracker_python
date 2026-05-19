from PyQt6 import QtWidgets as qw

import time_tracker
from time_tracker.api.client import FrappeAPI
from time_tracker.utils.logger import logger


class LoginDialog(qw.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to ERPNext")
        self.setModal(True)
        self.resize(450, 220)

        layout = qw.QVBoxLayout()

        layout.addWidget(qw.QLabel("Site URL"))
        self.url_input = qw.QLineEdit(time_tracker.config.get("credentials", {}).get("siteUrl", ""))
        layout.addWidget(self.url_input)

        layout.addWidget(qw.QLabel("API Key"))
        self.key_input = qw.QLineEdit(time_tracker.config.get("credentials", {}).get("apiKey", ""))
        layout.addWidget(self.key_input)

        layout.addWidget(qw.QLabel("API Secret"))
        self.secret_input = qw.QLineEdit(time_tracker.config.get("credentials", {}).get("apiSecret", ""))
        self.secret_input.setEchoMode(qw.QLineEdit.EchoMode.Password)
        layout.addWidget(self.secret_input)

        self.status_label = qw.QLabel("")
        layout.addWidget(self.status_label)

        buttons = qw.QHBoxLayout()
        test_btn = qw.QPushButton("Test Connection")
        save_btn = qw.QPushButton("Save & Continue")
        test_btn.clicked.connect(self.test_connection)
        save_btn.clicked.connect(self.save_and_continue)
        buttons.addWidget(test_btn)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def get_credentials(self):
        return {
            "siteUrl": self.url_input.text().strip(),
            "apiKey": self.key_input.text().strip(),
            "apiSecret": self.secret_input.text().strip(),
        }

    def test_connection(self):
        creds = self.get_credentials()
        if not all(creds.values()):
            self.status_label.setText("All fields are required.")
            self.status_label.setStyleSheet("color: red;")
            return
        try:
            logger.info("Testing connection to %s", creds["siteUrl"])
            test_api = FrappeAPI({"credentials": creds})
            test_api.projects()
            self.status_label.setText("Connection successful!")
            self.status_label.setStyleSheet("color: green;")
            logger.info("Connection test succeeded")
        except Exception as e:
            logger.warning("Connection test failed: %s", e)
            self.status_label.setText(f"Connection failed: {e}")
            self.status_label.setStyleSheet("color: red;")

    def save_and_continue(self):
        creds = self.get_credentials()
        if not all(creds.values()):
            self.status_label.setText("All fields are required.")
            self.status_label.setStyleSheet("color: red;")
            return
        logger.info("Saving credentials and continuing")
        time_tracker.config["credentials"] = creds
        time_tracker.save_config(time_tracker.config)
        time_tracker.erpnext = FrappeAPI(time_tracker.config)
        self.accept()
