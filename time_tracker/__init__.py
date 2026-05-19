from time_tracker.utils.logger import logger, patch_excepthook
from time_tracker.config import load_config, save_config

patch_excepthook()

config = load_config()

from time_tracker.api.client import FrappeAPI
erpnext = FrappeAPI(config)
logger.info("ERPNext client initialized: %s", config.get("credentials", {}).get("siteUrl", "?"))
