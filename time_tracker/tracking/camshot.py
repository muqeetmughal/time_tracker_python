import os
import re
import subprocess

from time_tracker.utils.logger import logger


SHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "shots")


def _ensure_shots_dir():
    os.makedirs(SHOTS_DIR, exist_ok=True)


def _filepath(activity_id):
    _ensure_shots_dir()
    existing = [f for f in os.listdir(SHOTS_DIR) if f.startswith(f"cam_{activity_id}_")]
    count = len(existing) + 1
    return os.path.join(SHOTS_DIR, f"cam_{activity_id}_{count}.jpg")


def list_cameras():
    """Return list of dicts with 'index' (int) and 'name' (str) for each video device."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stderr
    except Exception as e:
        logger.warning("Failed to list cameras: %s", e)
        return []

    cameras = []
    in_video = False
    for line in output.split("\n"):
        if "AVFoundation video devices:" in line:
            in_video = True
            continue
        if "AVFoundation audio devices:" in line:
            break
        if in_video:
            m = re.search(r'\[(\d+)\]\s(.+)', line)
            if m and "Capture screen" not in line:
                index = int(m.group(1))
                name = m.group(2).strip()
                cameras.append({"index": index, "name": name})

    return cameras


def capture(device_index, output_path=None):
    """Capture a single frame from the given camera device index."""
    if output_path is None:
        output_path = _filepath(str(device_index))

    try:
        cmd = [
            "ffmpeg", "-f", "avfoundation",
            "-video_device_index", str(device_index),
            "-r", "30",
            "-pixel_format", "uyvy422",
            "-i", f"{device_index}:none",
            "-vframes", "1",
            "-update", "1",
            "-y",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=True)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        logger.error("Camshot capture failed for device %s: %s", device_index, e)

    return None
