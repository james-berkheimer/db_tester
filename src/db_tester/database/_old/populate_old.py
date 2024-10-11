import traceback

from ..extensions import db
from ..plex import get_server
from ..utils.logging import LOGGER
from .helpers import get_out_of_date_data, get_playlists_to_add_and_remove
from .models import Episode, Movie, Photo, Playlist, Track
from .parsers import parse_playlist_item_updates, parse_playlists

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
        LOGGER.info("Starting database population process.")
        global db_playlists, plex_playlists
        initialize_globals()
        LOGGER.debug("Globals initialized")

        LOGGER.info("Getting playlists to add and remove")
        playlists_to_add, playlists_to_remove = get_playlists_to_add_and_remove(
            db_playlists, plex_playlists
        )

        new_playlist_check = True
        new_data_check = True

        if not playlists_to_add and not playlists_to_remove:
            LOGGER.info("No playlists to add or remove.")
            new_playlist_check = False

        else:
            LOGGER.info("Parsing playlists to add and remove")
            parse_playlists(
                playlists_to_add,
                playlists_to_remove,
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

        LOGGER.info("Getting out of date data")
        update_data = get_out_of_date_data(db_playlists, plex_playlists)

        if not update_data:
            LOGGER.info("No playlist item updates.")
            new_data_check = False

        else:
            LOGGER.info("Parsing playlist item updates")
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

        if new_playlist_check or new_data_check:
            LOGGER.info("Committing changes to the database")

            LOGGER.info(f"Adding {len(playlist_tracks_dict)} audio playlists to the database")
            audio_playlists = list(playlist_tracks_dict.keys())
            db.session.bulk_save_objects(audio_playlists)

            LOGGER.info(f"Adding {len(playlist_videos_dict)} video playlists to the database")
            video_playlists = list(playlist_videos_dict.keys())
            db.session.bulk_save_objects(video_playlists)

            LOGGER.info(f"Adding {len(playlist_photos_dict)} photo playlists to the database")
            photo_playlists = list(playlist_photos_dict.keys())
            db.session.bulk_save_objects(photo_playlists)
            db.session.commit()

            # Re-fetch playlists from the database to ensure they are properly associated
            db_playlists = {playlist.title: playlist for playlist in db.session.query(Playlist).all()}

            # Associate new items with playlists and commit them to the database if there are any
            LOGGER.info("Associating tracks with playlists")
            if playlist_tracks_dict:
                for db_playlist, tracks in playlist_tracks_dict.items():
                    db_playlist = db_playlists[db_playlist.title]
                    for db_track in tracks:
                        if db_track not in db_playlist.tracks:
                            db_playlist.tracks.append(db_track)
                    db.session.add(db_playlist)

            LOGGER.info("Associating videos with playlists")
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

            LOGGER.info("Associating photos with playlists")
            if playlist_photos_dict:
                for db_playlist, photos in playlist_photos_dict.items():
                    db_playlist = db_playlists[db_playlist.title]
                    for db_photo in photos:
                        if db_photo not in db_playlist.photos:
                            db_playlist.photos.append(db_photo)
                    db.session.add(db_playlist)

            # Remove items from playlists
            LOGGER.info("Disassociating items from playlists")
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
                    LOGGER.info(f"Disassociating {item.title} with {db_playlist.title}")
                db.session.add(db_playlist)

            # Commit the session to persist changes
            db.session.commit()

            # Commit new tracks, episodes, movies, and photos to the database if there are any
            if playlist_tracks_dict:
                LOGGER.info(
                    f"Adding {sum(len(tracks) for tracks in playlist_tracks_dict.values())} tracks to the database"
                )
                db.session.bulk_save_objects(
                    [track for tracks in playlist_tracks_dict.values() for track in tracks]
                )

            if playlist_videos_dict:
                LOGGER.info(
                    f"Adding {sum(len(videos) for videos in playlist_videos_dict.values())} videos to the database"
                )
                db.session.bulk_save_objects(
                    [video for videos in playlist_videos_dict.values() for video in videos]
                )

            if playlist_photos_dict:
                LOGGER.info(
                    f"Adding {sum(len(photos) for photos in playlist_photos_dict.values())} photos to the database"
                )
                db.session.bulk_save_objects(
                    [photo for photos in playlist_photos_dict.values() for photo in photos]
                )

            db.session.commit()

    except Exception as e:
        LOGGER.error("An error occurred during the database population process.", exc_info=True)
        traceback.print_exc()
        raise e
