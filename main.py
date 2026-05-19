import sys

from PyQt6 import QtWidgets as qw

import time_tracker
from time_tracker.utils.logger import logger
from time_tracker.ui.login_dialog import LoginDialog
from time_tracker.ui.main_window import TimeTrackerApp


def main():
    logger.info("=== Time Tracker starting ===")

    app = qw.QApplication(sys.argv)
    app.setApplicationName("Time Tracker")

    creds = time_tracker.config.get("credentials", {})
    if not creds.get("apiKey") or not creds.get("apiSecret"):
        login = LoginDialog()
        if login.exec() != qw.QDialog.DialogCode.Accepted:
            logger.info("Login cancelled by user")
            sys.exit(0)

    window = TimeTrackerApp()
    window.show()
    logger.info("Main window displayed")
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical("Fatal error during startup", exc_info=True)
        sys.exit(1)
