import requests

from PyQt6.QtCore import QThread, pyqtSignal

from time_tracker.config import load_config
from time_tracker.tracking.screenshot import capture as capture_screenshot
from time_tracker.tracking.camshot import capture as capture_camshot, list_cameras
from time_tracker.database import SessionLocal
from time_tracker.models import Activity, ActivityMedia
from time_tracker.utils.logger import logger


def _get_credentials():
    cfg = load_config()
    creds = cfg.get("credentials", {})
    return (
        creds.get("siteUrl", "http://localhost:8001"),
        creds.get("apiKey", ""),
        creds.get("apiSecret", ""),
    )


def upload_activity(activity):
    base_url, api_key, api_secret = _get_credentials()
    url = f"{base_url}/api/method/time_tracker.time_tracker.api.sync_time_tracker_record"

    payload = {
        "activity_id": activity.id,
        "project_id": activity.project_id,
        "task_id": activity.task_id,
        "activity_type": activity.activity_type,
        "description": activity.description,
        "start_time": activity.start_time.isoformat() if activity.start_time else None,
        "end_time": activity.end_time.isoformat() if activity.end_time else None,
        "duration_seconds": activity.duration_seconds,
        "screenshots_count": activity.screenshots_count,
        "camshots_count": activity.camshots_count,
        "keyboard_count": activity.keyboard_count,
        "mouse_click_count": activity.mouse_click_count,
        "status": activity.status,
    }

    headers = {
        "Authorization": f"token {api_key}:{api_secret}",
        "Content-Type": "application/json",
    }

    logger.info("Uploading activity %s to %s", activity.id, url)
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    logger.info("Activity %s synced successfully", activity.id)
    return True


def upload_media(media):
    base_url, api_key, api_secret = _get_credentials()
    url = f"{base_url}/api/method/time_tracker.time_tracker.api.sync_media"

    data = {
        "media_id": media.id,
        "activity_id": media.activity_id,
        "media_type": media.media_type,
        "filename": media.filename or "",
        "file_size": media.file_size,
        "status": media.status,
    }

    headers = {
        "Authorization": f"token {api_key}:{api_secret}",
    }

    files = None
    if media.file_data:
        files = {"file": (media.filename or f"{media.id}.png", media.file_data, "image/png")}

    logger.info("Uploading media %s to %s", media.id, url)
    resp = requests.post(url, data=data, files=files, headers=headers, timeout=60)
    resp.raise_for_status()
    logger.info("Media %s synced successfully", media.id)
    return True


class ScreenshotWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, activity_id, display=None):
        super().__init__()
        self.activity_id = activity_id
        self.display = display

    def run(self):
        try:
            path = capture_screenshot(self.activity_id, display=self.display)
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
    progress = pyqtSignal(str)

    def __init__(self, upload_activity_fn=None, upload_media_fn=None):
        super().__init__()
        self._upload_activity_fn = upload_activity_fn or upload_activity
        self._upload_media_fn = upload_media_fn or upload_media

    def run(self):
        db = SessionLocal()
        synced_count = 0
        try:
            pending_activity = (
                db.query(Activity)
                .filter(
                    Activity.sync_status == "pending",
                    Activity.status != "active",
                )
                .order_by(Activity.end_time.asc().nullsfirst())
                .first()
            )

            if pending_activity is not None:
                self.progress.emit(
                    f"Uploading: {pending_activity.description or pending_activity.id}"
                )
                try:
                    ok = self._upload_activity_fn(pending_activity)
                    if ok:
                        pending_media = (
                            db.query(ActivityMedia)
                            .filter(
                                ActivityMedia.activity_id == pending_activity.id,
                                ActivityMedia.sync_status == "pending",
                            )
                            .all()
                        )
                        for media in pending_media:
                            try:
                                if self._upload_media_fn(media):
                                    media.sync_status = "synced"
                                    synced_count += 1
                            except Exception as e:
                                logger.error(
                                    "UploadWorker: failed to sync media %s: %s",
                                    media.id, e,
                                )

                        pending_activity.sync_status = "synced"
                        synced_count += 1
                except Exception as e:
                    logger.error(
                        "UploadWorker: failed to sync activity %s: %s",
                        pending_activity.id, e,
                    )

                db.commit()
        except Exception as e:
            logger.error("UploadWorker error: %s", e)
            db.rollback()
        finally:
            db.close()

        self.finished.emit(synced_count)


class CamshotWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, activity_id, camera_index):
        super().__init__()
        self.activity_id = activity_id
        self.camera_index = camera_index

    def run(self):
        try:
            path = capture_camshot(self.camera_index)
            self.finished.emit(path)
        except Exception as e:
            logger.error("CamshotWorker error: %s", e)
            self.finished.emit(None)
