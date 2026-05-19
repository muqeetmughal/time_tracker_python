from PyQt6.QtCore import QThread, pyqtSignal

from time_tracker.tracking.screenshot import capture as capture_screenshot
from time_tracker.database import SessionLocal
from time_tracker.models import Activity
from time_tracker.utils.logger import logger


def mock_upload_activity(activity):
    """Mock upload to ERPNext — always succeeds."""
    logger.info("Mock upload: activity %s synced successfully", activity.id)
    return True


class ScreenshotWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, activity_id):
        super().__init__()
        self.activity_id = activity_id

    def run(self):
        try:
            path = capture_screenshot(self.activity_id)
            self.finished.emit(path)
        except Exception as e:
            logger.error("ScreenshotWorker error: %s", e)
            self.finished.emit(None)


class ApiWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, target, args=None, kwargs=None):
        super().__init__()
        self._target = target
        self._args = args or ()
        self._kwargs = kwargs or {}

    def run(self):
        try:
            result = self._target(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            logger.error("ApiWorker error for %s: %s", self._target.__name__, e)
            self.finished.emit(None)


class UploadWorker(QThread):
    finished = pyqtSignal(int)

    def __init__(self, upload_fn=None):
        super().__init__()
        self._upload_fn = upload_fn or mock_upload_activity

    def run(self):
        db = SessionLocal()
        synced_count = 0
        try:
            pending = (
                db.query(Activity)
                .filter(Activity.sync_status == "pending")
                .all()
            )

            for activity in pending:
                try:
                    ok = self._upload_fn(activity)
                    if ok:
                        activity.sync_status = "synced"
                        synced_count += 1
                except Exception as e:
                    logger.error("UploadWorker: failed to sync activity %s: %s", activity.id, e)

            db.commit()
        except Exception as e:
            logger.error("UploadWorker error: %s", e)
            db.rollback()
        finally:
            db.close()

        self.finished.emit(synced_count)
