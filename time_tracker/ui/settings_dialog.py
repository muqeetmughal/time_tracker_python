from PyQt6 import QtWidgets as qw

import time_tracker
from time_tracker.api.client import FrappeAPI
from time_tracker.utils.logger import logger


class SettingsDialog(qw.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(500, 420)

        self.tabs = qw.QTabWidget()
        self._build_connection_tab()
        self._build_general_tab()
        self._build_advanced_tab()
        self._build_sources_tab()
        self._build_other_tab()

        layout = qw.QVBoxLayout()
        layout.addWidget(self.tabs)

        buttons = qw.QHBoxLayout()
        save_btn = qw.QPushButton("Save")
        cancel_btn = qw.QPushButton("Cancel")
        save_btn.clicked.connect(self._save)
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def _add_checkbox(self, layout, label, section, key):
        cb = qw.QCheckBox(label)
        cb.setChecked(time_tracker.config.get("config", {}).get(section, {}).get(key, False))
        setattr(self, f"ck_{section}_{key}", cb)
        layout.addWidget(cb)

    def _add_spinbox(self, layout, label, section, key, lo=0, hi=999):
        row = qw.QHBoxLayout()
        row.addWidget(qw.QLabel(label))
        sb = qw.QSpinBox()
        sb.setRange(lo, hi)
        sb.setValue(time_tracker.config.get("config", {}).get(section, {}).get(key, 0))
        setattr(self, f"sb_{section}_{key}", sb)
        row.addWidget(sb)
        layout.addLayout(row)

    def _add_lineedit(self, layout, label, section, key):
        row = qw.QHBoxLayout()
        row.addWidget(qw.QLabel(label))
        le = qw.QLineEdit(time_tracker.config.get("config", {}).get(section, {}).get(key, ""))
        setattr(self, f"le_{section}_{key}", le)
        row.addWidget(le)
        layout.addLayout(row)

    def _add_combobox(self, layout, label, section, key, items):
        row = qw.QHBoxLayout()
        row.addWidget(qw.QLabel(label))
        cb = qw.QComboBox()
        for item in items:
            cb.addItem(item)
        val = time_tracker.config.get("config", {}).get(section, {}).get(key, items[0])
        idx = cb.findText(val)
        if idx >= 0:
            cb.setCurrentIndex(idx)
        setattr(self, f"cb_{section}_{key}", cb)
        row.addWidget(cb)
        layout.addLayout(row)

    def _build_connection_tab(self):
        tab = qw.QWidget()
        layout = qw.QVBoxLayout()
        creds = time_tracker.config.get("credentials", {})
        layout.addWidget(qw.QLabel("Site URL"))
        self.s_url = qw.QLineEdit(creds.get("siteUrl", ""))
        layout.addWidget(self.s_url)
        layout.addWidget(qw.QLabel("API Key"))
        self.s_key = qw.QLineEdit(creds.get("apiKey", ""))
        layout.addWidget(self.s_key)
        layout.addWidget(qw.QLabel("API Secret"))
        self.s_secret = qw.QLineEdit(creds.get("apiSecret", ""))
        self.s_secret.setEchoMode(qw.QLineEdit.EchoMode.Password)
        layout.addWidget(self.s_secret)
        layout.addStretch()
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Connection")

    def _build_general_tab(self):
        tab = qw.QWidget()
        layout = qw.QVBoxLayout()
        self._add_spinbox(layout, "Tracking Interval (min)", "general", "trackingIntervalMinutes", 1, 60)
        self._add_spinbox(layout, "Activity Update Interval (min)", "general", "activityUpdateIntervalMinutes", 1, 60)
        self._add_spinbox(layout, "Idle Timeout (min)", "general", "idleTimeoutMinutes", 1, 60)
        self._add_checkbox(layout, "Take Screenshots", "general", "takeScreenshots")
        self._add_checkbox(layout, "Take Camshots", "general", "takeCamshots")
        self._add_checkbox(layout, "Resume Tracking After Idle", "general", "resumeTrackingAfterIdle")
        self._add_checkbox(layout, "Review Images Before Upload", "general", "reviewImagesBeforeUpload")
        layout.addStretch()
        tab.setLayout(layout)
        self.tabs.addTab(tab, "General")

    def _build_advanced_tab(self):
        tab = qw.QWidget()
        layout = qw.QVBoxLayout()
        self._add_spinbox(layout, "Screenshot Review (sec)", "advanced", "screenshotReviewSeconds", 1, 60)
        self._add_checkbox(layout, "Randomized Tracking", "advanced", "randomizedTracking")
        self._add_checkbox(layout, "Activity Auto Complete", "advanced", "activityAutoComplete")
        self._add_checkbox(layout, "Ask Activity Update", "advanced", "askActivityUpdate")
        layout.addStretch()
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Advanced")

    def _build_sources_tab(self):
        tab = qw.QWidget()
        layout = qw.QVBoxLayout()
        self._add_checkbox(layout, "Count Keyboard Hits", "trackingSources", "countKeyboardHits")
        self._add_checkbox(layout, "Count Mouse Clicks", "trackingSources", "countMouseClicks")
        self._add_combobox(layout, "Screenshots From", "trackingSources", "screenshotsFrom", ["primary", "secondary"])
        self._add_lineedit(layout, "Camera ID", "trackingSources", "cameraId")
        self._add_lineedit(layout, "Camera Name", "trackingSources", "cameraName")
        layout.addStretch()
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Tracking Sources")

    def _build_other_tab(self):
        tab = qw.QWidget()
        layout = qw.QVBoxLayout()
        self._add_checkbox(layout, "Play Sounds", "other", "playSounds")
        self._add_checkbox(layout, "Show Dock Icon", "other", "showDockIcon")
        self._add_checkbox(layout, "Open at Login", "other", "openAtLogin")
        layout.addStretch()
        tab.setLayout(layout)
        self.tabs.addTab(tab, "Other")

    def _save(self):
        time_tracker.config["credentials"] = {
            "siteUrl": self.s_url.text().strip(),
            "apiKey": self.s_key.text().strip(),
            "apiSecret": self.s_secret.text().strip(),
        }

        sections = {
            "general": ["trackingIntervalMinutes", "activityUpdateIntervalMinutes", "idleTimeoutMinutes", "takeScreenshots", "takeCamshots", "resumeTrackingAfterIdle", "reviewImagesBeforeUpload"],
            "advanced": ["screenshotReviewSeconds", "randomizedTracking", "activityAutoComplete", "askActivityUpdate"],
            "trackingSources": ["countKeyboardHits", "countMouseClicks", "screenshotsFrom", "cameraId", "cameraName"],
            "other": ["playSounds", "showDockIcon", "openAtLogin"],
        }

        for section, fields in sections.items():
            for field in fields:
                wid = (getattr(self, f"sb_{section}_{field}", None) or
                       getattr(self, f"ck_{section}_{field}", None) or
                       getattr(self, f"le_{section}_{field}", None) or
                       getattr(self, f"cb_{section}_{field}", None))
                if wid is None:
                    continue
                if isinstance(wid, qw.QSpinBox):
                    time_tracker.config.setdefault("config", {}).setdefault(section, {})[field] = wid.value()
                elif isinstance(wid, qw.QCheckBox):
                    time_tracker.config.setdefault("config", {}).setdefault(section, {})[field] = wid.isChecked()
                elif isinstance(wid, qw.QLineEdit):
                    time_tracker.config.setdefault("config", {}).setdefault(section, {})[field] = wid.text().strip()
                elif isinstance(wid, qw.QComboBox):
                    time_tracker.config.setdefault("config", {}).setdefault(section, {})[field] = wid.currentText()

        time_tracker.save_config(time_tracker.config)
        time_tracker.erpnext = FrappeAPI(time_tracker.config)
        logger.info("Settings saved and API client reloaded")
        self.accept()
