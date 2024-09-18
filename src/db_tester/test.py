from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker

from .models import Playlist

db_path = "sqlite:///src/instance/db_tester.db"
# Create an engine and connect to the database
engine = create_engine(db_path)
metadata = MetaData()
metadata.reflect(bind=engine)
# Create a session
Session = sessionmaker(bind=engine)
session = Session()


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
    playlists = session.query(Playlist).all()
    for playlist in playlists:
        if playlist.playlist_type == "audio":
            items = playlist.tracks.all()
            for item in items:
                print(type(item))
