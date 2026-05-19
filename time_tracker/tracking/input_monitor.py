import ctypes
import ctypes.util
import json
import os
import subprocess
import sys
import tempfile
import time
import threading

from time_tracker.utils.logger import logger


class InputMonitor:
    def __init__(self):
        self.keyboard_count = 0
        self.mouse_click_count = 0
        self._running = False
        self._counts_file = None
        self._proc = None
        self._idle_func = None
        self._setup_idle()

    def _setup_idle(self):
        try:
            lib = ctypes.util.find_library("CoreGraphics")
            if not lib:
                logger.warning("CoreGraphics not found — idle detection disabled")
                return
            cg = ctypes.cdll.LoadLibrary(lib)
            fn = cg.CGEventSourceSecondsSinceLastEventType
            fn.restype = ctypes.c_double
            fn.argtypes = [ctypes.c_int32, ctypes.c_uint32]
            self._idle_func = lambda: fn(0, 0x80000000)
            logger.debug("Idle detection via ctypes CoreGraphics")
        except Exception as e:
            logger.warning("Idle detection setup failed: %s", e)

    # ---- lifecycle ----

    def start(self):
        if self._running:
            return
        self._running = True
        self.keyboard_count = 0
        self.mouse_click_count = 0
        self._start_listener()

    def stop(self):
        self._running = False
        if self._proc:
            self._proc.terminate()
            self._proc = None

    # ---- idle ----

    def seconds_since_last_event(self):
        if self._idle_func:
            try:
                return self._idle_func()
            except Exception as e:
                logger.debug("Idle query failed: %s", e)
        return 0.0

    def is_idle(self, timeout_seconds):
        return self.seconds_since_last_event() > timeout_seconds

    # ---- keyboard / mouse counts via isolated subprocess ----

    def _start_listener(self):
        script = os.path.join(os.path.dirname(__file__), "listener_script.py")
        if not os.path.exists(script):
            logger.debug("listener_script.py not found — input counting disabled")
            return
        try:
            self._counts_file = tempfile.mktemp(suffix="_tracker_counts.json")
            with open(self._counts_file, "w") as f:
                json.dump({"keyboard": 0, "mouse": 0}, f)
            self._proc = subprocess.Popen(
                [sys.executable, script, self._counts_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Input listener subprocess started (pid=%d)", self._proc.pid)
        except Exception as e:
            logger.warning("Could not start input listener subprocess: %s", e)
            self._proc = None

    def get_and_reset(self):
        k = self.keyboard_count
        m = self.mouse_click_count
        self.keyboard_count = 0
        self.mouse_click_count = 0

        if self._counts_file and os.path.exists(self._counts_file):
            try:
                with open(self._counts_file) as f:
                    data = json.load(f)
                k += data.get("keyboard", 0)
                m += data.get("mouse", 0)
                with open(self._counts_file, "w") as f:
                    json.dump({"keyboard": 0, "mouse": 0}, f)
            except Exception:
                pass

        return k, m
