# from db_tester.database.models import Episode, Movie

# from .database.helpers import get_add_remove_playlist_items, get_out_of_date_data
import logging
import os
import xml.etree.ElementTree as ET
from xml.etree import ElementTree

import requests
from plexapi.exceptions import BadRequest, NotFound, TwoFactorRequired, Unauthorized
from requests.status_codes import _codes as codes

from . import utils
from .database.extensions import session
from .database.helpers import get_out_of_date_data
from .database.models import Playlist
from .plex.server import get_server

logger = logging.getLogger("app_logger")


def test1():
    playlist_lst = session.query(Playlist).filter(Playlist.title == "Zeppelin").all()
    playlist = playlist_lst[0]
    print(f"{playlist.title}: {playlist.tracks.count()} tracks")
    items = playlist.tracks.all()
    for item in items:
        print(type(item))
        print(f"  ({item.track_number}) {item.title} - {item.album_title} - {item.artist_title}")


def test2():
    playlists = session.query(Playlist).all()
    # Sort playlists alphabetically by title
    playlists = sorted(playlists, key=lambda playlist: playlist.title)

    for playlist in playlists:
        if playlist.playlist_type == "audio":
            print(
                f"{playlist.title}: {playlist.tracks.count()} tracks | {int(playlist.duration / 100)} seconds"
            )
        elif playlist.playlist_type == "video":
            print(
                f"{playlist.title}: {playlist.episodes.count() + playlist.movies.count()} episodes & movies | {int(playlist.duration / 100)} seconds"
            )
        elif playlist.playlist_type == "photo":
            print(f"{playlist.title}: {playlist.photos.count()} photos")


def test3():
    plex_server = get_server()
    playlists = plex_server.playlists()
    for playlist in playlists:
        if playlist.playlistType == "audio":
            print(
                f"{playlist.title}: {len(playlist.items())} tracks | {int(playlist.duration / 100)} seconds"
            )
        if playlist.playlistType == "video":
            print(
                f"{playlist.title}: {len(playlist.items())} episodes & movies | {int(playlist.duration / 100)} seconds"
            )
        if playlist.playlistType == "photo":
            print(f"{playlist.title}: {len(playlist.items())} photos")


def test4():
    plex_server = get_server()
    playlists = plex_server.playlists()
    for playlist in playlists:
        if playlist.playlistType == "video" and playlist.title == "test video":
            print(f"{playlist.title}: {len(playlist.items())} episodes & movies")
            for item in playlist.items():
                if item.type == "episode":
                    print(f"{item.grandparentTitle}: {item.index}. {item.title}")
                else:
                    print(item.title)


def test5():
    # test_audio_playlist_1
    plex_server = get_server()
    sections = plex_server.library.sections()
    for section in sections:
        print(f"{section.title}: {section.key}")


def test6():
    db_playlists = session.query(Playlist).all()
    plex_server = get_server()
    plex_playlists = plex_server.playlists()

    out_of_date_data = get_out_of_date_data(db_playlists, plex_playlists)
    for playlist, add_remove in out_of_date_data.items():
        if playlist.playlist_type == "audio":
            add_tracks, remove_tracks = add_remove
            for add_track in add_tracks:
                print(f"Adding: {add_track.title} to db")
                print(f"Associating {add_track.title} with {playlist.title}\n")
            for remove_track in remove_tracks:
                print(f"Disassociating {remove_track.title} with {playlist.title}\n")
        if playlist.playlist_type == "video":
            add_videos, remove_videos = add_remove
            for add_video in add_videos:
                print(f"Adding: {add_video.title} to db")
                print(f"Associating {add_video.title} with {playlist.title}\n")
            for remove_video in remove_videos:
                print(f"Disassociating {remove_video.title} with {playlist.title}\n")

        if playlist.playlist_type == "photo":
            add_photos, remove_photos = add_remove
            print(f"{playlist.title}:")
            for photo in add_photos:
                print(f"Adding: {photo.title} to db")
                print(f"Associating {photo.title} with {playlist.title}\n")

            for photo in remove_photos:
                print(f"Disassociating {photo.title} with {playlist.title}\n")


def test7():
    # sectionId = 1
    # url = f"http://192.168.1.42:32400/library/sections/{sectionId}"
    url = "http://192.168.1.42:32400"
    playlists_url = url + "/playlists"

    api_key = os.getenv("PLEX_TOKEN")

    headers = {"X-Plex-Token": api_key}

    playlist_response = requests.request("GET", playlists_url, headers=headers)

    if playlist_response.status_code == 200:
        root = ET.fromstring(playlist_response.content)
        playlists = [
            (
                playlist.get("key"),
                playlist.get("title"),
                playlist.get("duration"),
                playlist.get("leafCount"),
                playlist.get("playlistType"),
            )
            for playlist in root.findall(".//Playlist")
        ]
        for key, title, duration, leaf_count, playlistType in playlists:
            if playlistType == "audio":
                print(f"Key: {key}, Title: {title}, Duration: {duration}, Leaf Count: {leaf_count}")
                items_response = requests.request("GET", url + key, headers=headers)
                if items_response.status_code == 200:
                    root = ET.fromstring(items_response.content)
                    items = [
                        (
                            item.get("key"),
                            item.get("title"),
                            item.get("duration"),
                            item.get("index"),
                            item.get("type"),
                            item.get("parentTitle"),
                            item.get("grandparentTitle"),
                        )
                        for item in root.findall(".//Track")
                    ]
                    for key, title, duration, index, item_type, parent_title, grandparent_title in items:
                        print(
                            f"\tKey: {key}, Type: {item_type}, Title: {grandparent_title}/{parent_title}/{title}, Index: {index}, Duration: {duration}"
                        )

    else:
        print(f"Failed to retrieve data: {playlist_response.status_code}")


# http://192.168.1.42:32400/web/index.html#!/


def test8():
    key = "https://plex.tv/api/v2/user"
    data = query(key)


def reset_base_headers():
    """Convenience function returns a dict of all base X-Plex-* headers for session requests."""
    import plexapi

    return {
        "X-Plex-Platform": plexapi.X_PLEX_PLATFORM,
        "X-Plex-Platform-Version": plexapi.X_PLEX_PLATFORM_VERSION,
        "X-Plex-Provides": plexapi.X_PLEX_PROVIDES,
        "X-Plex-Product": plexapi.X_PLEX_PRODUCT,
        "X-Plex-Version": plexapi.X_PLEX_VERSION,
        "X-Plex-Device": plexapi.X_PLEX_DEVICE,
        "X-Plex-Device-Name": plexapi.X_PLEX_DEVICE_NAME,
        "X-Plex-Client-Identifier": plexapi.X_PLEX_IDENTIFIER,
        "X-Plex-Language": plexapi.X_PLEX_LANGUAGE,
        "X-Plex-Sync-Version": "2",
        "X-Plex-Features": "external-media",
    }


def _headers(self, **kwargs):
    """Returns dict containing base headers for all requests to the server."""
    BASE_HEADERS = reset_base_headers()
    headers = BASE_HEADERS.copy()
    if self._token:
        headers["X-Plex-Token"] = self._token
    headers.update(kwargs)
    return headers


def query(url, method=None, headers=None, timeout=None, **kwargs):
    _session = requests.Session()
    method = method or _session.get
    timeout = 30
    logging.debug("%s %s %s", method.__name__.upper(), url, kwargs.get("json", ""))
    headers = _headers(**headers or {})
    response = method(url, headers=headers, timeout=timeout, **kwargs)
    if response.status_code not in (200, 201, 204):  # pragma: no cover
        codename = codes.get(response.status_code)[0]
        errtext = response.text.replace("\n", " ")
        message = f"({response.status_code}) {codename}; {response.url} {errtext}"
        if response.status_code == 401:
            if "verification code" in response.text:
                raise TwoFactorRequired(message)
            raise Unauthorized(message)
        elif response.status_code == 404:
            raise NotFound(message)
        elif response.status_code == 422 and "Invalid token" in response.text:
            raise Unauthorized(message)
        else:
            raise BadRequest(message)
    if "application/json" in response.headers.get("Content-Type", ""):
        return response.json()
    elif "text/plain" in response.headers.get("Content-Type", ""):
        return response.text.strip()
    data = utils.cleanXMLString(response.text).encode("utf8")
    return ElementTree.fromstring(data) if data.strip() else None
