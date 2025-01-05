import json
import logging
import os

import plexapi.exceptions as plex_exceptions

from ..config import PlexConfig
from .server import get_server

logger = logging.getLogger("app_logger")
__all__ = ["get_server", "plex_exceptions"]

try:
    with open(PlexConfig.CRED_PATH, "r") as f:
        data = json.load(f)
        plex_data = data.get("plex", {})
        os.environ["PLEX_BASEURL"] = plex_data.get("baseurl", "")
        os.environ["PLEX_TOKEN"] = plex_data.get("token", "")
        logger.debug("Loaded Plex credentials")

except FileNotFoundError as e:
    raise RuntimeError("Failed to load Plex credentials") from e
