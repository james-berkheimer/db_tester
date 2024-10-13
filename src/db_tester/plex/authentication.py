import os
from typing import Any, Dict, Optional


class AuthenticationError(Exception):
    pass


class Authentication:
    def __init__(self, auth_data: Optional[Dict[str, Any]] = None) -> None:
        self.auth_data = auth_data if auth_data else self._load_auth_data()

    def _load_auth_data(self) -> Dict[str, Any]:
        plex_baseurl = os.getenv("PLEX_BASEURL")
        plex_token = os.getenv("PLEX_TOKEN")

        if not plex_baseurl or not plex_token:
            raise AuthenticationError("PLEX_BASEURL or PLEX_TOKEN environment variables not set")

        return {"plex": {"baseurl": plex_baseurl, "token": plex_token}}

    @staticmethod
    def mask_auth_data(auth_data: Dict[str, Any]) -> Dict[str, Any]:
        masked_data = {
            k: (v if "token" not in k and "key" not in k else "****") for k, v in auth_data.items()
        }
        return masked_data


class PlexAuthentication(Authentication):
    def __init__(self, baseurl: Optional[str] = None, token: Optional[str] = None) -> None:
        auth_data = {"plex": {"baseurl": baseurl, "token": token}} if baseurl and token else None
        super().__init__(auth_data)

    @property
    def baseurl(self) -> str:
        return self.auth_data["plex"]["baseurl"]

    @property
    def token(self) -> str:
        return self.auth_data["plex"]["token"]
