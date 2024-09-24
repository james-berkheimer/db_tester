import traceback

from ..extensions import db
from ..models import Episode, Movie, Photo, Playlist, Track
from ..plex import get_server
from .helpers import (
    get_add_remove_playlists,
    get_out_of_date_data,
    parse_playlist_item_updates,
    parse_playlists,
)

# Globals vars
db_tracks_dict = {}
db_episode_dict = {}
db_movie_dict = {}
db_photo_dict = {}
playlist_tracks_dict = {}
playlist_videos_dict = {}
playlist_photos_dict = {}
remove_item_dict = {}


def initialize_globals():
    global plex_server, plex_playlists
    global db_playlists, db_tracks, db_episodes, db_movies, db_photos
    global db_playlist_dict, db_tracks_dict, db_episode_dict, db_movie_dict, db_photo_dict
    global playlist_tracks_dict, playlist_videos_dict, playlist_photos_dict

    # Global plex objects
    plex_server = get_server()
    plex_playlists = plex_server.playlists()

    # Global db objects
    db_playlists = db.session.query(Playlist).all()
    db_tracks = db.session.query(Track).all()
    db_episodes = db.session.query(Episode).all()
    db_movies = db.session.query(Movie).all()
    db_photos = db.session.query(Photo).all()
    db_playlist_dict = {db_playlist.title: db_playlist for db_playlist in db_playlists}
    db_tracks_dict = {
        (db_track.title, db_track.track_number, db_track.album_title, db_track.artist_name): db_track
        for db_track in db_tracks
    }
    db_episode_dict = {
        (
            db_episode.title,
            db_episode.episode_number,
            db_episode.season_number,
            db_episode.show_title,
        ): db_episode
        for db_episode in db_episodes
    }
    db_movie_dict = {
        (db_movie.title, db_movie.year, db_movie.duration): db_movie for db_movie in db_movies
    }
    db_photo_dict = {(db_photo.title, db_photo.thumbnail): db_photo for db_photo in db_photos}

    # Initialize playlist dictionaries
    playlist_tracks_dict.clear()
    playlist_videos_dict.clear()
    playlist_photos_dict.clear()
    remove_item_dict.clear()


def run_db_population():
    try:
        global db_playlists, plex_playlists

        # Initialize global variables
        initialize_globals()

        playlists_to_add, playlists_to_remove = get_add_remove_playlists(db_playlists, plex_playlists)

        # _parse_playlists(playlists_to_add)
        parse_playlists(
            playlists_to_add,
            plex_playlists,
            db_playlist_dict,
            db_tracks_dict,
            playlist_tracks_dict,
            db_episode_dict,
            db_movie_dict,
            playlist_videos_dict,
            db_photo_dict,
            playlist_photos_dict,
        )

        if playlists_to_remove:
            for playlist in playlists_to_remove:
                print(f"Removing playlist: {playlist} from the database")
                db_playlist = db_playlist_dict[playlist]
                db.session.delete(db_playlist)

        update_data = get_out_of_date_data(db_playlists, plex_playlists)
        parse_playlist_item_updates(
            update_data,
            db_tracks_dict,
            playlist_tracks_dict,
            db_episode_dict,
            db_movie_dict,
            playlist_videos_dict,
            db_photo_dict,
            playlist_photos_dict,
            remove_item_dict,
            plex_playlists,
        )

        # Commit new playlists to the database
        for db_playlist, tracks in playlist_tracks_dict.items():
            print(f"Adding playlist: {db_playlist.title}")

        print(f"Adding {len(playlist_tracks_dict)} audio playlists to the database")
        audio_playlists = list(playlist_tracks_dict.keys())
        db.session.bulk_save_objects(audio_playlists)

        video_playlists = list(playlist_videos_dict.keys())
        print(f"Adding {len(video_playlists)} video playlists to the database")
        db.session.bulk_save_objects(video_playlists)
        db.session.commit()

        photo_playlists = list(playlist_photos_dict.keys())
        print(f"Adding {len(photo_playlists)} photo playlists to the database")
        db.session.bulk_save_objects(photo_playlists)
        db.session.commit()

        # Re-fetch playlists from the database to ensure they are properly associated
        db_playlists = {playlist.title: playlist for playlist in db.session.query(Playlist).all()}

        # Associate tracks with playlists and commit new tracks to the database if there are any
        if playlist_tracks_dict:
            for db_playlist, tracks in playlist_tracks_dict.items():
                db_playlist = db_playlists[db_playlist.title]  # Ensure we use the managed instance
                for db_track in tracks:
                    if db_track not in db_playlist.tracks:
                        db_playlist.tracks.append(db_track)
                db.session.add(db_playlist)  # Explicitly add the playlist to the session

        # Associate episodes and movies with playlists and commit new episodes to the database if there are any
        if playlist_videos_dict:
            for db_playlist, items in playlist_videos_dict.items():
                print(f"Adding playlist: {db_playlist.title}")
                db_playlist = db_playlists[db_playlist.title]
                for db_item in items:
                    if type(db_item) is Episode:
                        if db_item not in db_playlist.episodes:
                            db_playlist.episodes.append(db_item)
                    elif type(db_item) is Movie:
                        if db_item not in db_playlist.movies:
                            db_playlist.movies.append(db_item)
                db.session.add(db_playlist)

        if playlist_photos_dict:
            for db_playlist, photos in playlist_photos_dict.items():
                db_playlist = db_playlists[db_playlist.title]
                for db_photo in photos:
                    if db_photo not in db_playlist.photos:
                        db_playlist.photos.append(db_photo)
                db.session.add(db_playlist)

        # Remove items from playlists
        for db_playlist, items in remove_item_dict.items():
            for item in items:
                if type(item) is Track:
                    db_playlist.tracks.remove(item)
                elif type(item) is Episode:
                    db_playlist.episodes.remove(item)
                elif type(item) is Movie:
                    db_playlist.movies.remove(item)
                elif type(item) is Photo:
                    db_playlist.photos.remove(item)
                print(f"Disassociating {item.title} with {db_playlist.title}")
            db.session.add(db_playlist)

        # Commit the session to persist changes
        db.session.commit()

        # Commit new tracks, episodes, movies, and photos to the database if there are any
        if playlist_tracks_dict:
            print(
                f"Adding {sum(len(tracks) for tracks in playlist_tracks_dict.values())} tracks to the database"
            )
            db.session.bulk_save_objects(
                [track for tracks in playlist_tracks_dict.values() for track in tracks]
            )

        if playlist_videos_dict:
            print(
                f"Adding {sum(len(videos) for videos in playlist_videos_dict.values())} videos to the database"
            )
            db.session.bulk_save_objects(
                [video for videos in playlist_videos_dict.values() for video in videos]
            )

        if playlist_photos_dict:
            print(
                f"Adding {sum(len(photos) for photos in playlist_photos_dict.values())} photos to the database"
            )
            db.session.bulk_save_objects(
                [photo for photos in playlist_photos_dict.values() for photo in photos]
            )

        db.session.commit()

    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        raise e
