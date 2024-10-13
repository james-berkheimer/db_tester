import json
import os

cred_path = "/home/james/code/db_tester/tests/.plex_cred/credentials.json"
with open(cred_path, "r") as f:
    data = json.load(f)
    plex_data = data.get("plex", {})
    os.environ["PLEX_BASEURL"] = plex_data.get("baseurl", "")
    os.environ["PLEX_TOKEN"] = plex_data.get("token", "")
