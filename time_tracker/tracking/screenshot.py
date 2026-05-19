import os
import subprocess
from datetime import datetime

from time_tracker.utils.logger import logger

SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "screenshots"
)


def _ensure_dir():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def _filepath(activity_id):
    _ensure_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(SCREENSHOTS_DIR, f"{activity_id}_{ts}.png")


def _screencapture(path):
    try:
        r = subprocess.run(
            ["/usr/sbin/screencapture", "-x", "-t", "png", path],
            capture_output=True, timeout=15
        )
        if r.returncode == 0 and os.path.getsize(path) > 0:
            logger.debug("Screenshot via screencapture: %s", path)
            return True
        logger.warning("screencapture failed (rc=%d)", r.returncode)
    except Exception as e:
        logger.warning("screencapture error: %s", e)
    return False


def _pil(path):
    try:
        from PIL import ImageGrab
        ImageGrab.grab().save(path)
        if os.path.getsize(path) > 0:
            logger.debug("Screenshot via PIL: %s", path)
            return True
    except Exception as e:
        logger.warning("PIL screenshot failed: %s", e)
    return False


def _mss(path):
    """Run mss in an isolated subprocess to avoid SIGILL crashes."""
    code = (
        "import mss; "
        "with mss.mss() as s: s.shot(output=%r)" % path
    )
    try:
        r = subprocess.run(
            [os.sys.executable, "-c", code],
            capture_output=True, timeout=15
        )
        if r.returncode == 0 and os.path.getsize(path) > 0:
            logger.debug("Screenshot via mss subprocess: %s", path)
            return True
    except Exception as e:
        logger.warning("mss subprocess failed: %s", e)
    return False


def capture(activity_id):
    path = _filepath(activity_id)

    if _screencapture(path):
        return path
    if _pil(path):
        return path
    if _mss(path):
        return path

    logger.error("All screenshot methods failed")
    return None
