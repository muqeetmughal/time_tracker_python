"""Runs as an isolated subprocess to safely use pynput.
If pynput is missing or crashes, this process silently dies —
the main app won't be affected."""

import json
import sys
import threading
import time

COUNTS_FILE = sys.argv[1]
k_count = 0
m_count = 0


def on_press(key):
    global k_count
    k_count += 1


def on_click(x, y, button, pressed):
    global m_count
    if pressed:
        m_count += 1


def flush():
    global k_count, m_count
    while True:
        time.sleep(2)
        try:
            with open(COUNTS_FILE) as f:
                prev = json.load(f)
            prev["keyboard"] = prev.get("keyboard", 0) + k_count
            prev["mouse"] = prev.get("mouse", 0) + m_count
            k_count = 0
            m_count = 0
            with open(COUNTS_FILE, "w") as f:
                json.dump(prev, f)
        except Exception:
            pass


if __name__ == "__main__":
    try:
        from pynput import keyboard, mouse

        t = threading.Thread(target=flush, daemon=True)
        t.start()

        with keyboard.Listener(on_press=on_press) as kl, mouse.Listener(
            on_click=on_click
        ) as ml:
            kl.join()
            ml.join()
    except Exception:
        sys.exit(1)
