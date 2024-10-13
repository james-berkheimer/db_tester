import json
import os

import plexapi.exceptions as plex_exceptions

from .server import get_server

__all__ = ["get_server", "plex_exceptions"]

cred_path = os.getenv("PLEX_CRED")
with open(cred_path, "r") as f:
    data = json.load(f)
    plex_data = data.get("plex", {})
    os.environ["PLEX_BASEURL"] = plex_data.get("baseurl", "")
    os.environ["PLEX_TOKEN"] = plex_data.get("token", "")
