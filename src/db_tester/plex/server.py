from plexapi.server import PlexServer

from .authentication import AuthenticationError, PlexAuthentication


def get_server():
    # Initialize Plex Authentication
    try:
        plex_auth = PlexAuthentication()
        # Create the Plex Server instance
        plex_server = PlexServer(baseurl=plex_auth.baseurl, token=plex_auth.token)
        return plex_server
    except AuthenticationError as e:
        raise RuntimeError("Failed to initialize Plex server") from e
