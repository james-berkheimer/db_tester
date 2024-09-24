from db_tester.models import Episode, Movie

from .database.helpers import get_add_remove_playlist_items, get_out_of_date_data
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
    plex_playlists = plex_server.playlists()
    db_playlist = session.query(Playlist).filter(Playlist.title == "test_audio_playlist_1").all()
    plex_playlist = next((pl for pl in plex_playlists if pl.title == db_playlist[0].title), None)
    print(f"Plex playlist: {plex_playlist.title}")


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
