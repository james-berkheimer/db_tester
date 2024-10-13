import logging
from typing import Dict, List, Tuple, Union

# from ..app import app
from .extensions import db
from .models import Episode, Movie, Photo, Playlist, Track

logger = logging.getLogger("app_logger")


def parse_playlists(
    playlists_to_add: List[str],
    playlists_to_remove: List[str],
    plex_playlists: List[object],
    db_playlist_dict: Dict[str, Playlist],
    db_tracks_dict: Dict[Tuple[str, int, str, str], Track],
    playlist_tracks_dict: Dict[Playlist, List[Track]],
    db_episode_dict: Dict[Tuple[str, int, int, str], Episode],
    db_movie_dict: Dict[Tuple[str, int, int], Movie],
    playlist_videos_dict: Dict[Playlist, List[Union[Episode, Movie]]],
    db_photo_dict: Dict[Tuple[str, str], Photo],
    playlist_photos_dict: Dict[Playlist, List[Photo]],
) -> None:
    """
    Parses playlists to add and remove.
    """

    try:
        if playlists_to_add:
            logger.info("Starting to parse playlists.")
            for plex_playlist_title in playlists_to_add:
                logger.debug(f"Processing playlist to add: {plex_playlist_title}")
                plex_playlist = next(
                    (pl for pl in plex_playlists if pl.title == plex_playlist_title), None
                )
                if not plex_playlist:
                    logger.warning(f"Playlist {plex_playlist_title} not found on Plex server.")
                    continue

                logger.debug(
                    f"Found playlist: {plex_playlist.title} with type: {plex_playlist.playlistType}"
                )

                if plex_playlist.playlistType == "audio":
                    logger.debug(f"Parsing audio playlist: {plex_playlist.title}")
                    _parse_audio_playlist(
                        db_playlist_dict, db_tracks_dict, playlist_tracks_dict, plex_playlist
                    )
                elif plex_playlist.playlistType == "video":
                    logger.debug(f"Parsing video playlist: {plex_playlist.title}")
                    _parse_video_playlist(
                        db_playlist_dict,
                        db_episode_dict,
                        db_movie_dict,
                        playlist_videos_dict,
                        plex_playlist,
                    )
                elif plex_playlist.playlistType == "photo":
                    logger.debug(f"Parsing photo playlist: {plex_playlist.title}")
                    _parse_photo_playlist(
                        db_playlist_dict, db_photo_dict, playlist_photos_dict, plex_playlist
                    )
                else:
                    logger.warning(f"Unknown playlist type: {plex_playlist.playlistType}")

        if playlists_to_remove:
            logger.info("Starting to remove playlists.")
            logger.debug(f"Playlists to remove: {playlists_to_remove}")
            _update_remove_playlists(playlists_to_remove, db_playlist_dict)

    except Exception as e:
        logger.error("An error occurred while parsing playlists.", exc_info=True)
        db.session.rollback()
        raise e


def parse_playlist_item_updates(
    update_data: Dict[Playlist, Tuple[List[object], List[object]]],
    db_tracks_dict: Dict[Tuple[str, int, str, str], Track],
    playlist_tracks_dict: Dict[Playlist, List[Track]],
    db_episode_dict: Dict[Tuple[str, int, int, str], Episode],
    db_movie_dict: Dict[Tuple[str, int, int], Movie],
    playlist_videos_dict: Dict[Playlist, List[Union[Episode, Movie]]],
    db_photo_dict: Dict[Tuple[str, str], Photo],
    playlist_photos_dict: Dict[Playlist, List[Photo]],
    remove_item_dict: Dict[Playlist, List[Union[Track, Episode, Movie, Photo]]],
    plex_playlists: List[object],
) -> bool:
    """
    Parses playlist item updates.
    """
    try:
        logger.info("Starting to parse playlist item updates.")
        for db_playlist, add_remove_items in update_data.items():
            remove_item_dict[db_playlist] = []
            playlist_tracks_dict[db_playlist] = []
            playlist_videos_dict[db_playlist] = []
            playlist_photos_dict[db_playlist] = []

            if db_playlist.playlist_type == "audio":
                _update_audio_playlist(
                    add_remove_items, db_tracks_dict, playlist_tracks_dict, remove_item_dict, db_playlist
                )
            elif db_playlist.playlist_type == "video":
                _update_video_playlist(
                    add_remove_items,
                    db_episode_dict,
                    db_movie_dict,
                    playlist_videos_dict,
                    remove_item_dict,
                    db_playlist,
                )
            elif db_playlist.playlist_type == "photo":
                _update_photo_playlist(
                    add_remove_items, db_photo_dict, playlist_photos_dict, remove_item_dict, db_playlist
                )
            else:
                logger.warning(f"Unknown playlist type: {db_playlist.playlist_type}")

            _update_playlist_duration(db_playlist, plex_playlists)
            logger.debug(f"Updated playlist: {db_playlist.title} with duration: {db_playlist.duration}")

        return True

    except Exception as e:
        logger.error("An error occurred while updating playlist items.", exc_info=True)
        db.session.rollback()
        raise e


def _parse_audio_playlist(
    db_playlist_dict: Dict[str, Playlist],
    db_tracks_dict: Dict[Tuple[str, int, str, str], Track],
    playlist_tracks_dict: Dict[Playlist, List[Track]],
    plex_playlist: object,
) -> None:
    """
    Parses an audio playlist.
    """
    try:
        db_playlist = _get_or_create_playlist(db_playlist_dict, plex_playlist)
        plex_tracks = plex_playlist.items()
        playlist_tracks_dict[db_playlist] = []

        for plex_track in plex_tracks:
            plex_album = plex_track.album()
            plex_artist = plex_track.artist()
            track_key = (plex_track.title, plex_track.trackNumber, plex_album.title, plex_artist.title)
            if track_key not in db_tracks_dict:
                db_tracks_dict[track_key] = Track(
                    title=plex_track.title,
                    track_number=plex_track.trackNumber,
                    album_title=plex_album.title,
                    artist_name=plex_artist.title,
                    duration=plex_track.duration,
                )

            db_track = db_tracks_dict[track_key]
            playlist_tracks_dict[db_playlist].append(db_track)

    except Exception as e:
        logger.error("An error occurred while parsing audio playlist.", exc_info=True)
        db.session.rollback()
        raise e


def _parse_photo_playlist(
    db_playlist_dict: Dict[str, Playlist],
    db_photo_dict: Dict[Tuple[str, str], Photo],
    playlist_photos_dict: Dict[Playlist, List[Photo]],
    plex_playlist: object,
) -> None:
    """
    Parses a photo playlist.
    """
    try:
        db_playlist = _get_or_create_playlist(db_playlist_dict, plex_playlist)
        plex_photos = plex_playlist.items()
        playlist_photos_dict[db_playlist] = []

        for plex_photo in plex_photos:
            photo_key = (plex_photo.title, plex_photo.thumb)
            if photo_key not in db_photo_dict:
                db_photo_dict[photo_key] = Photo(
                    title=plex_photo.title,
                    thumbnail=plex_photo.thumb,
                    file=plex_photo.media[0].parts[0].file,
                )
            db_photo = db_photo_dict[photo_key]
            playlist_photos_dict[db_playlist].append(db_photo)

    except Exception as e:
        logger.error("An error occurred while parsing photo playlist.", exc_info=True)
        db.session.rollback()
        raise e


def _parse_video_playlist(
    db_playlist_dict: Dict[str, Playlist],
    db_episode_dict: Dict[Tuple[str, int, int, str], Episode],
    db_movie_dict: Dict[Tuple[str, int, int], Movie],
    playlist_videos_dict: Dict[Playlist, List[Union[Episode, Movie]]],
    plex_playlist: object,
) -> None:
    """
    Parses a video playlist.
    """
    try:
        db_playlist = _get_or_create_playlist(db_playlist_dict, plex_playlist)
        plex_videos = plex_playlist.items()
        playlist_videos_dict[db_playlist] = []

        for plex_video in plex_videos:
            if plex_video.type == "episode":
                plex_show = plex_video.show()
                plex_season = plex_video.season()
                episode_key = (
                    plex_video.title,
                    plex_video.index,
                    plex_season.index,
                    plex_show.title,
                )
                if episode_key not in db_episode_dict:
                    db_episode_dict[episode_key] = Episode(
                        title=plex_video.title,
                        episode_number=plex_video.index,
                        duration=plex_video.duration,
                        season_number=plex_season.index,
                        show_title=plex_show.title,
                        show_year=plex_show.year,
                    )
                db_episode = db_episode_dict[episode_key]
                playlist_videos_dict[db_playlist].append(db_episode)
            elif plex_video.type == "movie":
                movie_key = (plex_video.title, plex_video.year, plex_video.duration)
                if movie_key not in db_movie_dict:
                    db_movie_dict[movie_key] = Movie(
                        title=plex_video.title,
                        year=plex_video.year,
                        duration=plex_video.duration,
                        thumbnail=plex_video.thumb,
                    )
                db_movie = db_movie_dict[movie_key]
                playlist_videos_dict[db_playlist].append(db_movie)

    except Exception as e:
        logger.error("An error occurred while parsing video playlist.", exc_info=True)
        db.session.rollback()
        raise e


def _update_audio_playlist(
    add_remove_items: Tuple[List[object], List[Track]],
    db_tracks_dict: Dict[Tuple[str, int, str, str], Track],
    playlist_tracks_dict: Dict[Playlist, List[Track]],
    remove_item_dict: Dict[Playlist, List[Union[Track, Episode, Movie, Photo]]],
    db_playlist: Playlist,
) -> None:
    """
    Updates an audio playlist.
    """
    try:
        add_plex_tracks, remove_db_tracks = add_remove_items
        for plex_track in add_plex_tracks:
            plex_album = plex_track.album()
            plex_artist = plex_track.artist()
            track_key = (plex_track.title, plex_track.trackNumber, plex_album.title, plex_artist.title)
            db_track = db_tracks_dict.get(track_key) or Track(
                title=plex_track.title,
                track_number=plex_track.trackNumber,
                album_title=plex_album.title,
                artist_name=plex_artist.title,
                duration=plex_track.duration,
            )
            db_tracks_dict[track_key] = db_track
            playlist_tracks_dict[db_playlist].append(db_track)

        for db_track in remove_db_tracks:
            remove_item_dict[db_playlist].append(db_track)

    except Exception as e:
        logger.error("An error occurred in update_audio_playlist.", exc_info=True)
        db.session.rollback()
        raise e


def _update_photo_playlist(
    add_remove_items: Tuple[List[Photo], List[Photo]],
    db_photo_dict: Dict[Tuple[str, str], Photo],
    playlist_photos_dict: Dict[Playlist, List[Photo]],
    remove_item_dict: Dict[Playlist, List[Union[Track, Episode, Movie, Photo]]],
    db_playlist: Playlist,
) -> None:
    """
    Updates a photo playlist.
    """
    try:
        add_photos, remove_photos = add_remove_items
        for db_photo in add_photos:
            photo_key = (db_photo.title, db_photo.thumbnail)
            db_photo = db_photo_dict.get(photo_key) or Photo(
                title=db_photo.title,
                thumbnail=db_photo.thumbnail,
                file=db_photo.file,
            )
            db_photo_dict[photo_key] = db_photo
            playlist_photos_dict[db_playlist].append(db_photo)

        for db_photo in remove_photos:
            remove_item_dict[db_playlist].append(db_photo)

    except Exception as e:
        logger.error("An error occurred in update_photo_playlist.", exc_info=True)
        db.session.rollback()
        raise e


def _update_video_playlist(
    add_remove_items: Tuple[List[object], List[Union[Episode, Movie]]],
    db_episode_dict: Dict[Tuple[str, int, int, str], Episode],
    db_movie_dict: Dict[Tuple[str, int, int], Movie],
    playlist_videos_dict: Dict[Playlist, List[Union[Episode, Movie]]],
    remove_item_dict: Dict[Playlist, List[Union[Track, Episode, Movie, Photo]]],
    db_playlist: Playlist,
) -> None:
    """
    Updates a video playlist.
    """
    try:
        add_plex_videos, remove_db_videos = add_remove_items
        for plex_video in add_plex_videos:
            if plex_video.type == "episode":
                episode_key = (
                    plex_video.title,
                    plex_video.index,
                    plex_video.seasonNumber,
                    plex_video.title,
                )
                db_episode = db_episode_dict.get(episode_key) or Episode(
                    title=plex_video.title,
                    episode_number=plex_video.index,
                    season_number=plex_video.seasonNumber,
                    show_title=plex_video.title,
                    duration=plex_video.duration,
                )
                db_episode_dict[episode_key] = db_episode
                playlist_videos_dict[db_playlist].append(db_episode)
            elif plex_video.type == "movie":
                movie_key = (plex_video.title, plex_video.year, plex_video.duration)
                db_movie = db_movie_dict.get(movie_key) or Movie(
                    title=plex_video.title,
                    year=plex_video.year,
                    duration=plex_video.duration,
                )
                db_movie_dict[movie_key] = db_movie
                playlist_videos_dict[db_playlist].append(db_movie)

        for db_video in remove_db_videos:
            remove_item_dict[db_playlist].append(db_video)

    except Exception as e:
        logger.error("An error occurred in update_video_playlist.", exc_info=True)
        db.session.rollback()
        raise e


def _update_remove_playlists(
    playlists_to_remove: List[str], db_playlist_dict: Dict[str, Playlist]
) -> None:
    """
    Removes playlists from the database.
    """
    try:
        for playlist in playlists_to_remove:
            logger.info(f"Removing playlist: {playlist} from the database")
            db_playlist = db_playlist_dict[playlist]
            db.session.delete(db_playlist)
        db.session.commit()
    except Exception as e:
        logger.error("An error occurred while removing playlists.", exc_info=True)
        db.session.rollback()
        raise e


def _update_playlist_duration(db_playlist: Playlist, plex_playlists: List[object]) -> None:
    """
    Updates the duration of a playlist.
    """
    try:
        plex_playlist = next(
            (playlist for playlist in plex_playlists if playlist.title == db_playlist.title), None
        )
        if plex_playlist:
            db_playlist.duration = plex_playlist.duration
            db.session.add(db_playlist)
            db.session.commit()
        else:
            logger.warning(f"Skipping playlist: {db_playlist.title} (not found on Plex server)")
    except Exception as e:
        logger.error("Error in update_playlist_duration", exc_info=True)
        db.session.rollback()
        raise e


def _get_or_create_playlist(db_playlist_dict: Dict[str, Playlist], plex_playlist: object) -> Playlist:
    """
    Gets or creates a playlist.
    """
    if plex_playlist.title not in db_playlist_dict:
        db_playlist = Playlist(
            title=plex_playlist.title,
            playlist_type=plex_playlist.playlistType,
            duration=plex_playlist.duration,
            thumbnail=plex_playlist.thumb,
        )
        db_playlist_dict[plex_playlist.title] = db_playlist
    else:
        db_playlist = db_playlist_dict[plex_playlist.title]
    return db_playlist
