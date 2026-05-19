import os
import random
from datetime import timezone
import uuid

from PyQt6 import QtWidgets as qw
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QColor

import time_tracker
from time_tracker.database import SessionLocal
from time_tracker.models import Activity, ActivityMedia, ActivityInput, utc_now
from time_tracker.tracking.input_monitor import InputMonitor
from time_tracker.ui.activity_dialog import ActivityDialog
from time_tracker.ui.settings_dialog import SettingsDialog
from time_tracker.utils.workers import ScreenshotWorker, ApiWorker
from time_tracker.utils.logger import logger


THUMB_SIZE = 60


class TimeTrackerApp(qw.QWidget):
    def __init__(self):
        super().__init__()
        logger.info("Initializing TimeTrackerApp")

        self.db = SessionLocal()
        self.session_id = str(uuid.uuid4())
        self.active_activity = None
        self._update_dialog_open = False
        self._paused = False
        self._screenshot_worker = None
        self._api_workers = []

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_timer)

        self.screenshot_timer = QTimer()
        self.screenshot_timer.timeout.connect(self._on_screenshot_timer)

        self.activity_update_timer = QTimer()
        self.activity_update_timer.timeout.connect(self._on_activity_update_timer)

        self.input_monitor = InputMonitor()

        self._last_input_save = None

        self.setWindowTitle("Time Tracker")
        self.resize(680, 600)

        self._build_ui_async()
        self._load_activities()
        self._load_screenshots()
        self._update_ui_state()

    def _build_ui_async(self):
        layout = qw.QVBoxLayout()

        # ---- header ----
        header = qw.QHBoxLayout()
        title = qw.QLabel("Time Tracker")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header.addWidget(title)

        self.status_label = qw.QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: orange;")
        header.addWidget(self.status_label)

        header.addStretch()

        self.timer_label = qw.QLabel("00:00:00")
        self.timer_label.setStyleSheet("font-size: 20px; font-weight: bold; color: gray;")
        header.addWidget(self.timer_label)

        self.settings_btn = qw.QPushButton("\u2699")
        self.settings_btn.setFixedWidth(36)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self._open_settings)
        header.addWidget(self.settings_btn)

        layout.addLayout(header)

        # ---- project row ----
        self.project_input = qw.QComboBox()
        self.project_input.addItem("-- Select Project --", None)

        project_row = qw.QHBoxLayout()
        project_row.addWidget(qw.QLabel("Project"))
        project_row.addWidget(self.project_input, 1)

        self.toggle_btn = qw.QPushButton("Start Tracking")
        self.toggle_btn.clicked.connect(self._toggle_tracking)
        project_row.addWidget(self.toggle_btn)
        layout.addLayout(project_row)

        # ---- activities table ----
        self.table = qw.QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Description", "Activity Type", "Project", "Task",
            "Start", "End", "Duration", "Screenshots", "Keys", "Status"
        ])
        layout.addWidget(self.table, 3)

        # ---- screenshots section ----
        layout.addWidget(qw.QLabel("Screenshots"))
        self.shot_table = qw.QTableWidget()
        self.shot_table.setColumnCount(4)
        self.shot_table.setHorizontalHeaderLabels(["Preview", "Filename", "Size", "Status"])
        self.shot_table.setEditTriggers(qw.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.shot_table.verticalHeader().setDefaultSectionSize(THUMB_SIZE + 8)
        layout.addWidget(self.shot_table, 2)

        self.setLayout(layout)
        self._refresh_projects_async()

    # ---- async API helpers ----

    def _refresh_projects_async(self):
        worker = ApiWorker(time_tracker.erpnext.projects)
        worker.finished.connect(self._on_projects_loaded)
        worker.finished.connect(worker.deleteLater)
        self._api_workers.append(worker)
        worker.start()

    def _on_projects_loaded(self, projects):
        self._api_workers = [w for w in self._api_workers if not w.isFinished()]
        if not projects:
            logger.warning("No projects returned from API")
            return
        self.project_input.clear()
        self.project_input.addItem("-- Select Project --", None)
        for project in projects:
            self.project_input.addItem(
                f"{project['name']} ({project['project_name']})", project['name']
            )
        logger.debug("Loaded %d projects", len(projects))

    # ---- settings ----

    def _open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()
        self._refresh_projects_async()

    def closeEvent(self, event):
        logger.info("Shutting down")
        self.input_monitor.stop()
        super().closeEvent(event)

    # ---- config helpers ----

    def _cfg(self, *keys, default=None):
        val = time_tracker.config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k, {})
            else:
                return default
        return val if val is not None else default

    def _interval_ms(self, *keys, fallback_ms=60000):
        minutes = self._cfg(*keys, default=1)
        return max(int(minutes) * 60 * 1000, 30000)

    # ---- timers ----

    def _start_timers(self):
        self.timer.start(1000)
        self._schedule_screenshot()
        self._schedule_activity_update()

        cfg = self._cfg("config", "trackingSources", default={})
        if cfg.get("countKeyboardHits") or cfg.get("countMouseClicks"):
            self.input_monitor.start()
        logger.info("Tracking timers started")

    def _schedule_screenshot(self):
        ms = self._interval_ms("config", "general", "trackingIntervalMinutes")
        if self._cfg("config", "advanced", "randomizedTracking", default=False):
            ms = int(ms * random.uniform(0.8, 1.2))
        self.screenshot_timer.start(ms)

    def _schedule_activity_update(self):
        ms = self._interval_ms("config", "general", "activityUpdateIntervalMinutes")
        self.activity_update_timer.start(ms)

    def _stop_timers(self):
        self.timer.stop()
        self.screenshot_timer.stop()
        self.activity_update_timer.stop()
        self.input_monitor.stop()
        logger.info("Tracking timers stopped")

    def _pause_timers(self):
        self.screenshot_timer.stop()
        self.activity_update_timer.stop()

    def _resume_timers(self):
        self._schedule_screenshot()
        self._schedule_activity_update()

    # ---- idle ----

    def _check_idle(self):
        cfg = self._cfg("config", "general", default={})
        idle_timeout = cfg.get("idleTimeoutMinutes", 0)
        if idle_timeout <= 0:
            return

        if not self.active_activity or self._paused:
            if self._paused and self.input_monitor.seconds_since_last_event() < 5:
                self._resume_from_idle()
            return

        if self.input_monitor.is_idle(idle_timeout * 60):
            logger.info("Idle timeout reached (%d min)", idle_timeout)
            self._enter_idle()

    def _enter_idle(self):
        self._paused = True
        self._pause_timers()
        self._save_input_counts()
        if self.active_activity:
            self.active_activity.status = "idle"
            self.db.commit()
        self.status_label.setText("IDLE")
        self.status_label.setStyleSheet("font-size: 12px; color: orange;")
        self._load_activities()

    def _resume_from_idle(self):
        if not self._paused:
            return
        self._paused = False
        self.status_label.setText("")
        self._resume_timers()
        logger.info("Resumed from idle")

        if self._cfg("config", "general", "resumeTrackingAfterIdle", default=False):
            if self.active_activity:
                self.active_activity.status = "active"
                self.db.commit()
                self._load_activities()

    # ---- auto-complete ----

    def _check_auto_complete(self):
        if not self.active_activity or self._paused:
            return
        if not self._cfg("config", "advanced", "activityAutoComplete", default=False):
            return

        expected = self.active_activity.expected_hours
        if not expected or expected <= 0:
            return

        start = self.active_activity.start_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        elapsed = (utc_now() - start).total_seconds() / 3600

        if elapsed >= expected:
            logger.info("Auto-completing activity after %.1f hours", elapsed)
            self._stop_tracking()
            self.status_label.setText("Auto-completed")
            self.status_label.setStyleSheet("font-size: 12px; color: green;")
            QTimer.singleShot(5000, lambda: self.status_label.setText(""))

    # ---- toggle ----

    def _toggle_tracking(self):
        if self.active_activity:
            self._stop_tracking()
        else:
            self._start_tracking()

    def _update_ui_state(self):
        tracking = self.active_activity is not None
        self.toggle_btn.setText("Stop Tracking" if tracking else "Start Tracking")
        self.project_input.setEnabled(not tracking)
        self.settings_btn.setEnabled(not tracking)

    def _start_tracking(self):
        if self.active_activity:
            qw.QMessageBox.warning(self, "Already Tracking", "Tracking is already active.")
            return

        project_id = self.project_input.currentData()
        if not project_id:
            qw.QMessageBox.warning(self, "No Project", "Please select a project.")
            return

        dialog = ActivityDialog(project_id, self)
        if dialog.exec() != qw.QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        if not data:
            return

        activity = Activity(
            session_id=self.session_id,
            project_id=project_id,
            task_id=data["task_id"],
            activity_type=data["activity_type"],
            description=data["description"],
            expected_hours=data["expected_hours"],
            start_time=utc_now(),
            status="active"
        )

        self.db.add(activity)
        self.db.commit()
        logger.info("Started tracking activity %s on project %s", activity.id, project_id)

        self._paused = False
        self.status_label.setText("")
        self._last_input_save = utc_now()
        self.active_activity = activity
        self._start_timers()
        self._load_activities()
        self._update_ui_state()

    def _do_update_activity(self):
        project_id = self.project_input.currentData()

        current = self.active_activity
        current_data = {
            "activity_type": current.activity_type,
            "task_id": current.task_id,
            "expected_hours": current.expected_hours,
            "description": current.description,
        }

        dialog = ActivityDialog(project_id, self, current_data=current_data)
        if dialog.exec() != qw.QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        if not data:
            return

        self._save_input_counts()

        current.close()
        logger.debug("Closed previous activity %s", current.id)

        new_activity = Activity(
            session_id=self.session_id,
            project_id=project_id,
            task_id=data["task_id"],
            activity_type=data["activity_type"],
            description=data["description"],
            expected_hours=data["expected_hours"],
            start_time=utc_now(),
            status="active"
        )

        self.db.add(new_activity)
        self.db.commit()

        self.active_activity = new_activity
        self._load_activities()

    def _stop_tracking(self):
        if not self.active_activity:
            qw.QMessageBox.warning(self, "Not Tracking", "No active tracking session.")
            return

        self._save_input_counts()
        self._stop_timers()

        self.active_activity.close()
        self.db.commit()
        logger.info("Stopped tracking activity %s", self.active_activity.id)

        self.active_activity = None
        self._paused = False
        self.status_label.setText("")
        self.timer_label.setText("00:00:00")
        self._load_activities()
        self._update_ui_state()

    def _save_input_counts(self):
        activity = self.active_activity
        if not activity:
            return

        cfg = self._cfg("config", "trackingSources", default={})
        kb, mouse = self.input_monitor.get_and_reset()

        if cfg.get("countKeyboardHits"):
            activity.keyboard_count = (activity.keyboard_count or 0) + kb
        if cfg.get("countMouseClicks"):
            activity.mouse_click_count = (activity.mouse_click_count or 0) + mouse

        now = utc_now()
        inp = ActivityInput(
            activity_id=activity.id,
            keyboard_count=kb,
            mouse_click_count=mouse,
            started_at=self._last_input_save or activity.start_time,
            ended_at=now,
        )
        self.db.add(inp)
        self._last_input_save = now

    # ---- screenshot (async) ----

    def _on_screenshot_timer(self):
        if not self.active_activity or self._paused:
            self._schedule_screenshot()
            return
        cfg = self._cfg("config", "general", default={})
        if not cfg.get("takeScreenshots"):
            self._schedule_screenshot()
            return

        self._save_input_counts()
        self.db.commit()

        activity = self.active_activity

        self._screenshot_worker = ScreenshotWorker(activity.id)
        self._screenshot_worker.finished.connect(self._on_screenshot_done)
        self._screenshot_worker.finished.connect(self._screenshot_worker.deleteLater)
        self._screenshot_worker.start()

    def _on_screenshot_done(self, path):
        if not path or not self.active_activity:
            self._schedule_screenshot()
            return

        self.active_activity.screenshots_count = (self.active_activity.screenshots_count or 0) + 1

        file_data = None
        try:
            with open(path, "rb") as f:
                file_data = f.read()
        except Exception as e:
            logger.warning("Failed to read screenshot file: %s", e)

        media = ActivityMedia(
            activity_id=self.active_activity.id,
            media_type="screenshot",
            filename=os.path.basename(path),
            file_data=file_data,
            file_size=len(file_data) if file_data else 0,
            file_path=path,
            status="approved",
        )
        self.db.add(media)
        self.db.commit()

        self._load_activities()
        self._load_screenshots()
        logger.debug("Screenshot captured: %s (media_id=%s)", path, media.id)

        self._schedule_screenshot()

    # ---- screenshots grid ----

    def _load_screenshots(self):
        try:
            media_list = (
                self.db.query(ActivityMedia)
                .order_by(ActivityMedia.created_at.desc())
                .all()
            )

            self.shot_table.setRowCount(len(media_list))

            for row, m in enumerate(media_list):
                # thumbnail
                pix = None
                if m.file_data:
                    pix = QPixmap()
                    pix.loadFromData(m.file_data)
                if pix and not pix.isNull():
                    thumb = pix.scaled(
                        THUMB_SIZE, THUMB_SIZE,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    lbl = qw.QLabel()
                    lbl.setPixmap(thumb)
                    self.shot_table.setCellWidget(row, 0, lbl)
                else:
                    self.shot_table.setItem(row, 0, qw.QTableWidgetItem("N/A"))

                # filename
                self.shot_table.setItem(row, 1, qw.QTableWidgetItem(m.filename or ""))

                # size
                size_str = f"{m.file_size} B" if m.file_size else ""
                if m.file_size and m.file_size > 1024:
                    size_str = f"{m.file_size / 1024:.1f} KB"
                self.shot_table.setItem(row, 2, qw.QTableWidgetItem(size_str))

                # status
                status_item = qw.QTableWidgetItem(m.status or "unknown")
                if m.status == "approved":
                    status_item.setForeground(QColor(100, 200, 100))
                elif m.status == "rejected":
                    status_item.setForeground(QColor(200, 100, 100))
                elif m.status == "pending":
                    status_item.setForeground(QColor(200, 200, 80))
                self.shot_table.setItem(row, 3, status_item)

            self.shot_table.resizeColumnsToContents()
            self.shot_table.setColumnWidth(0, THUMB_SIZE + 12)
        except Exception as e:
            logger.error("Failed to load screenshots: %s", e)

    # ---- periodic activity update ----

    def _on_activity_update_timer(self):
        if not self.active_activity or self._update_dialog_open or self._paused:
            self._schedule_activity_update()
            return
        cfg = self._cfg("config", "advanced", default={})
        if not cfg.get("askActivityUpdate"):
            self._schedule_activity_update()
            return

        self._update_dialog_open = True
        try:
            self._do_update_activity()
        finally:
            self._update_dialog_open = False
            self._schedule_activity_update()

    # ---- tables ----

    def _load_activities(self):
        try:
            activities = (
                self.db.query(Activity)
                .filter(Activity.session_id == self.session_id)
                .order_by(Activity.start_time.asc())
                .all()
            )

            self.table.setRowCount(len(activities))

            for row, activity in enumerate(activities):
                duration = activity.duration_seconds or 0
                values = [
                    activity.description,
                    activity.activity_type or "",
                    activity.project_id or "",
                    activity.task_id or "",
                    str(activity.start_time),
                    str(activity.end_time or ""),
                    f"{duration}s",
                    str(activity.screenshots_count),
                    str(activity.keyboard_count),
                    activity.status,
                ]
                for col, value in enumerate(values):
                    self.table.setItem(row, col, qw.QTableWidgetItem(value))
        except Exception as e:
            logger.error("Failed to load activities: %s", e)

    def _update_timer(self):
        if self.active_activity and not self._paused:
            try:
                start_time = self.active_activity.start_time
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                elapsed = (utc_now() - start_time).total_seconds()
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                self.timer_label.setStyleSheet("font-size: 20px; font-weight: bold; color: green;")

                self._check_idle()
                self._check_auto_complete()
            except Exception as e:
                logger.error("Timer tick error: %s", e)
        else:
            self.timer_label.setStyleSheet("font-size: 20px; font-weight: bold; color: gray;")
