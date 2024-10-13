import logging
import traceback
from typing import Dict, List, Optional, Tuple

from ..plex import get_server

# from ..app import app
from .extensions import db
from .helpers import get_out_of_date_data, get_playlists_to_add_and_remove
from .models import Episode, Movie, Photo, Playlist, Track
from .parsers import parse_playlist_item_updates, parse_playlists

logger = logging.getLogger("app_logger")


class DatabasePopulator:
    """
    Class responsible for populating the database with data from the Plex server.
    """

    def __init__(self):
        """
        Initializes the DatabasePopulator with empty dictionaries and None values for server and playlists.
        """
        self.db_tracks_dict: Dict[Tuple[str, int, str, str], Track] = {}
        self.db_episode_dict: Dict[Tuple[str, int, int, str], Episode] = {}
        self.db_movie_dict: Dict[Tuple[str, int, int], Movie] = {}
        self.db_photo_dict: Dict[Tuple[str, str], Photo] = {}
        self.playlist_tracks_dict: Dict[Playlist, List[Track]] = {}
        self.playlist_videos_dict: Dict[Playlist, List[Episode | Movie]] = {}
        self.playlist_photos_dict: Dict[Playlist, List[Photo]] = {}
        self.remove_item_dict: Dict[Playlist, List[Track | Episode | Movie | Photo]] = {}

        self.plex_server: Optional[object] = None
        self.plex_playlists: Optional[List[Playlist]] = None
        self.db_playlists: Optional[List[Playlist]] = None
        self.db_playlist_dict: Optional[Dict[str, Playlist]] = None

    def initialize_globals(self) -> None:
        """
        Initializes global variables by fetching data from the Plex server and the database.
        """
        self.plex_server = get_server()
        self.plex_playlists = self.plex_server.playlists()

        self.db_playlists = db.session.query(Playlist).all()
        db_tracks = db.session.query(Track).all()
        db_episodes = db.session.query(Episode).all()
        db_movies = db.session.query(Movie).all()
        db_photos = db.session.query(Photo).all()

        self.db_playlist_dict = {db_playlist.title: db_playlist for db_playlist in self.db_playlists}
        self.db_tracks_dict = {
            (db_track.title, db_track.track_number, db_track.album_title, db_track.artist_name): db_track
            for db_track in db_tracks
        }
        self.db_episode_dict = {
            (
                db_episode.title,
                db_episode.episode_number,
                db_episode.season_number,
                db_episode.show_title,
            ): db_episode
            for db_episode in db_episodes
        }
        self.db_movie_dict = {
            (db_movie.title, db_movie.year, db_movie.duration): db_movie for db_movie in db_movies
        }
        self.db_photo_dict = {(db_photo.title, db_photo.thumbnail): db_photo for db_photo in db_photos}

        self.playlist_tracks_dict.clear()
        self.playlist_videos_dict.clear()
        self.playlist_photos_dict.clear()
        self.remove_item_dict.clear()

    def run_db_population(self) -> None:
        """
        Runs the database population process by initializing globals, getting out-of-date data, and committing changes to the database.
        """

        try:
            logger.info("Starting database population process.")
            self.initialize_globals()
            logger.debug("Globals initialized")

            playlists_to_add, playlists_to_remove = self.get_playlists_to_add_and_remove()
            new_playlist_check = self.check_and_parse_playlists(playlists_to_add, playlists_to_remove)
            new_data_check = self.check_and_parse_out_of_date_data()

            if new_playlist_check or new_data_check:
                self.commit_changes_to_db()

        except Exception as e:
            logger.error("An error occurred during the database population process.", exc_info=True)
            traceback.print_exc()
            raise e

    def get_playlists_to_add_and_remove(self) -> Tuple[List[Playlist], List[Playlist]]:
        """
        Gets the playlists to add and remove.

        Returns:
            Tuple[List[Playlist], List[Playlist]]: Playlists to add and remove.
        """
        logger.info("Getting playlists to add and remove")
        return get_playlists_to_add_and_remove(self.db_playlists, self.plex_playlists)

    def check_and_parse_playlists(
        self, playlists_to_add: List[Playlist], playlists_to_remove: List[Playlist]
    ) -> bool:
        """
        Checks and parses playlists to add and remove.

        Args:
            playlists_to_add (List[Playlist]): Playlists to add.
            playlists_to_remove (List[Playlist]): Playlists to remove.

        Returns:
            bool: True if there are playlists to add or remove, False otherwise.
        """
        if not playlists_to_add and not playlists_to_remove:
            logger.info("No playlists to add or remove.")
            return False

        logger.info("Parsing playlists to add and remove")
        parse_playlists(
            playlists_to_add,
            playlists_to_remove,
            self.plex_playlists,
            self.db_playlist_dict,
            self.db_tracks_dict,
            self.playlist_tracks_dict,
            self.db_episode_dict,
            self.db_movie_dict,
            self.playlist_videos_dict,
            self.db_photo_dict,
            self.playlist_photos_dict,
        )
        return True

    def check_and_parse_out_of_date_data(self) -> bool:
        """
        Checks and parses out-of-date data.

        Returns:
            bool: True if there is out-of-date data, False otherwise.
        """
        logger.info("Getting out of date data")
        update_data = get_out_of_date_data(self.db_playlists, self.plex_playlists)

        if not update_data:
            logger.info("No playlist item updates.")
            return False

        logger.info("Parsing playlist item updates")
        parse_playlist_item_updates(
            update_data,
            self.db_tracks_dict,
            self.playlist_tracks_dict,
            self.db_episode_dict,
            self.db_movie_dict,
            self.playlist_videos_dict,
            self.db_photo_dict,
            self.playlist_photos_dict,
            self.remove_item_dict,
            self.plex_playlists,
        )
        return True

    def commit_changes_to_db(self) -> None:
        """
        Commits changes to the database by saving new objects and associating/disassociating items with playlists.
        """
        logger.info("Committing changes to the database")

        self.bulk_save_objects(self.playlist_tracks_dict, "audio playlists")
        self.bulk_save_objects(self.playlist_videos_dict, "video playlists")
        self.bulk_save_objects(self.playlist_photos_dict, "photo playlists")

        self.db_playlists = {playlist.title: playlist for playlist in db.session.query(Playlist).all()}

        self.associate_items_with_playlists(self.playlist_tracks_dict, "tracks")
        self.associate_items_with_playlists(self.playlist_videos_dict, "videos")
        self.associate_items_with_playlists(self.playlist_photos_dict, "photos")

        self.disassociate_items_from_playlists()

        db.session.commit()

    def bulk_save_objects(
        self, playlist_dict: Dict[Playlist, List[Track | Episode | Movie | Photo]], playlist_type: str
    ) -> None:
        """
        Bulk saves objects to the database.

        Args:
            playlist_dict (Dict): Dictionary of playlists and their items.
            playlist_type (str): Type of playlist (audio, video, photo).
        """
        logger.info(f"Adding/Updating {len(playlist_dict)} {playlist_type} to the database")
        db.session.bulk_save_objects(list(playlist_dict.keys()))
        db.session.commit()

    def associate_items_with_playlists(
        self, playlist_dict: Dict[Playlist, List[Track | Episode | Movie | Photo]], item_type: str
    ) -> None:
        """
        Associates items with playlists.

        Args:
            playlist_dict (Dict): Dictionary of playlists and their items.
            item_type (str): Type of item (tracks, videos, photos).
        """
        logger.info(f"Associating {item_type} with playlists")
        for db_playlist, items in playlist_dict.items():
            db_playlist = self.db_playlists[db_playlist.title]
            for item in items:
                if item_type == "tracks" and item not in db_playlist.tracks:
                    db_playlist.tracks.append(item)
                elif item_type == "videos":
                    if isinstance(item, Episode) and item not in db_playlist.episodes:
                        db_playlist.episodes.append(item)
                    elif isinstance(item, Movie) and item not in db_playlist.movies:
                        db_playlist.movies.append(item)
                elif item_type == "photos" and item not in db_playlist.photos:
                    db_playlist.photos.append(item)
            db.session.add(db_playlist)

    def disassociate_items_from_playlists(self) -> None:
        """
        Disassociates items from playlists.
        """
        logger.info("Disassociating items from playlists")
        for db_playlist, items in self.remove_item_dict.items():
            for item in items:
                if isinstance(item, Track):
                    db_playlist.tracks.remove(item)
                elif isinstance(item, Episode):
                    db_playlist.episodes.remove(item)
                elif isinstance(item, Movie):
                    db_playlist.movies.remove(item)
                elif isinstance(item, Photo):
                    db_playlist.photos.remove(item)
                logger.info(f"Disassociating {item.title} with {db_playlist.title}")
            db.session.add(db_playlist)


if __name__ == "__main__":
    populator = DatabasePopulator()
    populator.run_db_population()
