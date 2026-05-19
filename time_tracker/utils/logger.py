import logging
import os
import sys
import traceback

LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs"
)


def setup_logger():
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("time_tracker")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(os.path.join(LOG_DIR, "app.log"), mode="a")
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    logger.handlers.clear()
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


logger = setup_logger()


def log_exception(exc_type, exc_value, exc_tb):
    logger.critical(
        "Unhandled exception",
        exc_info=(exc_type, exc_value, exc_tb)
    )


def patch_excepthook():
    sys.excepthook = log_exception


patch_excepthook()
