from PyQt6 import QtWidgets as qw

import time_tracker
from time_tracker.utils.logger import logger


class ActivityDialog(qw.QDialog):
    def __init__(self, project_id, parent=None, current_data=None):
        super().__init__(parent)
        self.setWindowTitle("Update Activity" if current_data else "Activity Details")
        self.setModal(True)
        self.resize(400, 350)

        layout = qw.QVBoxLayout()

        try:
            activities = time_tracker.erpnext.activity_types()
        except Exception as e:
            logger.warning("Failed to fetch activity types: %s", e)
            activities = []
        self.activity_type_input = qw.QComboBox()
        self.activity_type_input.setEditable(True)
        for activity in activities:
            self.activity_type_input.addItem(activity['name'])

        try:
            tasks = time_tracker.erpnext.tasks(project_id)
        except Exception as e:
            logger.warning("Failed to fetch tasks for project %s: %s", project_id, e)
            tasks = []
        self.task_input = qw.QComboBox()
        self.task_input.addItem("-- No Task --", None)
        for task in tasks:
            self.task_input.addItem(f"{task['name']} ({task['subject']})", task['name'])

        self.expected_hours_input = qw.QDoubleSpinBox()
        self.expected_hours_input.setRange(0, 999)
        self.expected_hours_input.setDecimals(2)
        self.expected_hours_input.setSingleStep(0.5)
        self.expected_hours_input.setSuffix(" hrs")

        self.description_input = qw.QPlainTextEdit()
        self.description_input.setPlaceholderText("Activity Description")

        layout.addWidget(qw.QLabel("Activity Type"))
        layout.addWidget(self.activity_type_input)
        layout.addWidget(qw.QLabel("Task"))
        layout.addWidget(self.task_input)
        layout.addWidget(qw.QLabel("Expected Hours"))
        layout.addWidget(self.expected_hours_input)
        layout.addWidget(qw.QLabel("Description"))
        layout.addWidget(self.description_input)

        buttons = qw.QHBoxLayout()
        submit_btn = qw.QPushButton("Update" if current_data else "Start")
        cancel_btn = qw.QPushButton("Cancel")
        submit_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(submit_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

        if current_data:
            self._prefill(current_data)

    def _prefill(self, data):
        if data.get("activity_type"):
            idx = self.activity_type_input.findText(data["activity_type"])
            if idx >= 0:
                self.activity_type_input.setCurrentIndex(idx)
            else:
                self.activity_type_input.setEditText(data["activity_type"])

        if data.get("task_id"):
            idx = self.task_input.findData(data["task_id"])
            if idx >= 0:
                self.task_input.setCurrentIndex(idx)

        if data.get("expected_hours"):
            self.expected_hours_input.setValue(data["expected_hours"])

        if data.get("description"):
            self.description_input.setPlainText(data["description"])

    def get_data(self):
        description = self.description_input.toPlainText().strip()
        if not description:
            qw.QMessageBox.warning(self, "Missing Description", "Activity description is required.")
            return None
        return {
            "activity_type": self.activity_type_input.currentText().strip() or None,
            "task_id": self.task_input.currentData(),
            "expected_hours": self.expected_hours_input.value() or None,
            "description": description,
        }
