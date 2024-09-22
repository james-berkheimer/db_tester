import os

from .extensions import session
from .models import Playlist
from .plex.server import get_server


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
    for playlist in playlists:
        if playlist.playlist_type == "audio":
            print(
                f"{playlist.title}: {playlist.tracks.count()} tracks | {int(playlist.duration / 100)} seconds"
            )
        if playlist.playlist_type == "video":
            print(
                f"{playlist.title}: {playlist.episodes.count() + playlist.movies.count()} episodes & movies | {int(playlist.duration / 100)} seconds"
            )
        if playlist.playlist_type == "photo":
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
    playlists = session.query(Playlist).all()
    for playlist in playlists:
        if playlist.playlist_type == "video" and playlist.title == "test video":
            print(
                f"{playlist.title}: {playlist.episodes.count()+ playlist.movies.count()} episodes & movies"
            )
            for episode in playlist.episodes.all():
                print(f"  {episode.show_title}: {episode.episode_number}. {episode.title}")
            for movie in playlist.movies.all():
                print(f"  {movie.title}")


def test6():
    print(os.getenv("SQLALCHEMY_DATABASE_URI"))
