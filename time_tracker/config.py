import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

DEFAULT = {
    "credentials": {
        "siteUrl": "http://localhost:8001",
        "apiKey": "",
        "apiSecret": ""
    },
    "config": {
        "general": {
            "trackingIntervalMinutes": 1,
            "activityUpdateIntervalMinutes": 1,
            "idleTimeoutMinutes": 1,
            "takeScreenshots": True,
            "takeCamshots": True,
            "resumeTrackingAfterIdle": True,
            "reviewImagesBeforeUpload": True
        },
        "advanced": {
            "screenshotReviewSeconds": 10,
            "randomizedTracking": True,
            "activityAutoComplete": True,
            "askActivityUpdate": True
        },
        "trackingSources": {
            "countKeyboardHits": True,
            "countMouseClicks": True,
            "screenshotsFrom": "primary",
            "cameraId": "",
            "cameraName": ""
        },
        "other": {
            "playSounds": True,
            "showDockIcon": True,
            "openAtLogin": False
        }
    }
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    save_config(DEFAULT)
    return DEFAULT


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
