import os
import subprocess
import ctypes
import ctypes.util
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


def list_displays():
    """Return list of dicts with 'index' (int, 1-based) and 'name' for each active display."""
    displays = []
    try:
        lib_path = ctypes.util.find_library("CoreGraphics")
        if lib_path is None:
            raise RuntimeError("CoreGraphics not found")
        cg = ctypes.cdll.LoadLibrary(lib_path)

        CGGetActiveDisplayList = cg.CGGetActiveDisplayList
        CGGetActiveDisplayList.argtypes = [
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        CGGetActiveDisplayList.restype = ctypes.c_int32

        CGMainDisplayID = cg.CGMainDisplayID
        CGMainDisplayID.restype = ctypes.c_uint32

        count = ctypes.c_uint32()
        max_displays = 16
        displays_arr = (ctypes.c_uint32 * max_displays)()
        err = CGGetActiveDisplayList(max_displays, displays_arr, ctypes.byref(count))

        if err != 0:
            raise RuntimeError(f"CGGetActiveDisplayList error: {err}")

        main_id = CGMainDisplayID()
        for i in range(count.value):
            display_id = displays_arr[i]
            name = "Main Display" if display_id == main_id else f"Display {i + 1}"
            displays.append({"index": i + 1, "name": name, "id": display_id})
    except Exception as e:
        logger.warning("Failed to enumerate displays: %s", e)
        displays.append({"index": 1, "name": "Main Display", "id": 0})

    if not displays:
        displays.append({"index": 1, "name": "Main Display", "id": 0})

    return displays


def _screencapture(path, display=None):
    try:
        cmd = ["/usr/sbin/screencapture", "-x", "-t", "png"]
        if display is not None:
            cmd.append(f"-D{display}")
        cmd.append(path)
        r = subprocess.run(cmd, capture_output=True, timeout=15)
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


def _mss(path, display=None):
    """Run mss in an isolated subprocess to avoid SIGILL crashes."""
    if display is not None:
        code = (
            "import mss; "
            "with mss.mss() as s: "
            "  mon = s.monitors[%d]; "
            "  s.get_pixels(mon); "
            "  s.to_png().save(%r)" % (display, path)
        )
    else:
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


def capture(activity_id, display=None):
    path = _filepath(activity_id)

    if _screencapture(path, display=display):
        return path
    if _pil(path):
        return path
    if _mss(path, display=display):
        return path

    logger.error("All screenshot methods failed")
    return None
