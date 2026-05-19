from PyQt6.QtCore import QThread, pyqtSignal

from time_tracker.tracking.screenshot import capture as capture_screenshot
from time_tracker.utils.logger import logger


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
