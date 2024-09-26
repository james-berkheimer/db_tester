import traceback

from ..extensions import db
from ..models import Episode, Movie, Photo, Playlist, Track
from ..utils.logging import LOGGER


def parse_playlists(
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
):
    try:
        if playlists_to_add:
            LOGGER.info("Starting to parse playlists.")
            for plex_playlist_title in playlists_to_add:
                plex_playlist = next(
                    (pl for pl in plex_playlists if pl.title == plex_playlist_title), None
                )
                if plex_playlist.playlistType == "audio":
                    _parse_audio_playlist(
                        db_playlist_dict, db_tracks_dict, playlist_tracks_dict, plex_playlist
                    )
                elif plex_playlist.playlistType == "video":
                    _parse_video_playlist(
                        db_playlist_dict,
                        db_episode_dict,
                        db_movie_dict,
                        playlist_videos_dict,
                        plex_playlist,
                    )
                elif plex_playlist.playlistType == "photo":
                    _parse_photo_playlist(
                        db_playlist_dict,
                        db_photo_dict,
                        playlist_photos_dict,
                        plex_playlist,
                    )
                else:
                    LOGGER.debug(f"Skipping playlist: {plex_playlist.title}")

        elif playlists_to_remove:
            LOGGER.info("Starting to remove playlists.")
            _update_remove_playlists(playlists_to_remove, db_playlist_dict)

        else:
            LOGGER.warning("No playlists to add or remove")

    except Exception as e:
        LOGGER.error("An error occurred while parsing playlists.", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e


def parse_playlist_item_updates(
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
):
    try:
        LOGGER.info("Starting to parse playlist item updates.")
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
                LOGGER.warning(f"Skipping playlist: {db_playlist.title}")

            # Updating the playlist duration
            _update_playlist_duration(db_playlist, plex_playlists)
            LOGGER.debug(f"Updated playlist: {db_playlist.title} with duration: {db_playlist.duration}")

    except Exception as e:
        LOGGER.error("An error occurred while updating playlist items.", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e


def _parse_audio_playlist(db_playlist_dict, db_tracks_dict, playlist_tracks_dict, plex_playlist):
    try:
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

        plex_tracks = plex_playlist.items()
        playlist_tracks_dict[db_playlist] = []

        for plex_track in plex_tracks:
            plex_album = plex_track.album()
            plex_artist = plex_track.artist()
            track_key = (plex_track.title, plex_track.trackNumber, plex_album.title, plex_artist.title)
            if track_key not in db_tracks_dict:
                db_track = Track(
                    title=plex_track.title,
                    track_number=plex_track.trackNumber,
                    duration=plex_track.duration,
                    album_title=plex_album.title,
                    album_year=plex_album.year,
                    artist_name=plex_artist.title,
                )
                db_tracks_dict[track_key] = db_track
            else:
                db_track = db_tracks_dict[track_key]

            playlist_tracks_dict[db_playlist].append(db_track)
    except Exception as e:
        LOGGER.error("An error occurred while parsing audio playlist.", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e


def _parse_photo_playlist(db_playlist_dict, db_photo_dict, playlist_photos_dict, plex_playlist):
    try:
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

        plex_photos = plex_playlist.items()
        playlist_photos_dict[db_playlist] = []

        for plex_photo in plex_photos:
            photo_key = (plex_photo.title, plex_photo.thumb)
            if photo_key not in db_photo_dict:
                db_photo = Photo(
                    title=plex_photo.title,
                    thumbnail=plex_photo.thumb,
                    file=plex_photo.media[0].parts[0].file,
                )
                db_photo_dict[photo_key] = db_photo
            else:
                db_photo = db_photo_dict[photo_key]

            playlist_photos_dict[db_playlist].append(db_photo)

    except Exception as e:
        LOGGER.error("An error occurred while parsing photo playlist.", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e


def _parse_video_playlist(
    db_playlist_dict,
    db_episode_dict,
    db_movies_dict,
    playlist_videos_dict,
    plex_playlist,
):
    try:
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

        plex_videos = plex_playlist.items()
        playlist_videos_dict[db_playlist] = []

        for plex_video in plex_videos:
            if plex_video.type == "episode":
                plex_show = plex_video.show()
                plex_season = plex_video.season()
                episode_key = (plex_video.title, plex_video.index, plex_season.index, plex_show.title)
                if episode_key not in db_episode_dict:
                    db_episode = Episode(
                        title=plex_video.title,
                        episode_number=plex_video.index,
                        duration=plex_video.duration,
                        season_number=plex_season.index,
                        show_title=plex_show.title,
                        show_year=plex_show.year,
                    )
                    db_episode_dict[episode_key] = db_episode
                else:
                    db_episode = db_episode_dict[episode_key]

                playlist_videos_dict[db_playlist].append(db_episode)
            elif plex_video.type == "movie":
                movie_key = (plex_video.title, plex_video.year, plex_video.duration)
                if movie_key not in db_movies_dict:
                    db_movie = Movie(
                        title=plex_video.title,
                        year=plex_video.year,
                        duration=plex_video.duration,
                        thumbnail=plex_video.thumb,
                    )
                    db_movies_dict[movie_key] = db_movie
                else:
                    db_movie = db_movies_dict[movie_key]

                playlist_videos_dict[db_playlist].append(db_movie)

    except Exception as e:
        LOGGER.error("An error occurred while parsing video playlist.", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e


def _update_audio_playlist(
    add_remove_items, db_tracks_dict, playlist_tracks_dict, remove_item_dict, db_playlist
):
    try:
        add_plex_tracks, remove_db_tracks = add_remove_items
        for plex_track in add_plex_tracks:
            plex_album = plex_track.album()
            plex_artist = plex_track.artist()
            track_key = (
                plex_track.title,
                plex_track.trackNumber,
                plex_album.title,
                plex_artist.title,
            )
            if track_key not in db_tracks_dict:
                db_track = Track(
                    title=plex_track.title,
                    track_number=plex_track.trackNumber,
                    duration=plex_track.duration,
                    album_title=plex_album.title,
                    album_year=plex_album.year,
                    artist_name=plex_artist.title,
                )
                db_tracks_dict[track_key] = db_track
            else:
                db_track = db_tracks_dict[track_key]

            playlist_tracks_dict[db_playlist].append(db_track)

        for db_track in remove_db_tracks:
            remove_item_dict[db_playlist].append(db_track)

    except Exception as e:
        LOGGER.error("An error occurred in update_audio_playlist.", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e


def _update_photo_playlist(
    add_remove_items, db_photo_dict, playlist_photos_dict, remove_item_dict, db_playlist
):
    try:
        add_photos, remove_photos = add_remove_items
        for db_photo in add_photos:
            photo_key = (db_photo.title, db_photo.thumbnail)
            if photo_key not in db_photo_dict:
                db_photo = Photo(title=db_photo.title, thumbnail=db_photo.thumbnail)
                db_photo_dict[photo_key] = db_photo
            else:
                db_photo = db_photo_dict[photo_key]

            playlist_photos_dict[db_playlist].append(db_photo)
        for db_photo in remove_photos:
            remove_item_dict[db_playlist].append(db_photo)

    except Exception as e:
        LOGGER.error("An error occurred in update_photo_playlist.", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e


def _update_video_playlist(
    add_remove_items, db_episode_dict, db_movie_dict, playlist_videos_dict, remove_item_dict, db_playlist
):
    try:
        add_plex_videos, remove_db_videos = add_remove_items
        for plex_video in add_plex_videos:
            if plex_video.type == "episode":
                plex_show = plex_video.show()
                episode_key = (
                    plex_video.title,
                    plex_video.index,
                    plex_video.seasonNumber,
                    plex_show.title,
                )
                if episode_key not in db_episode_dict:
                    db_episode = Episode(
                        title=plex_video.title,
                        episode_number=plex_video.index,
                        season_number=plex_video.seasonNumber,
                        show_title=plex_show.title,
                        duration=plex_video.duration,
                    )
                    db_episode_dict[episode_key] = db_episode
                else:
                    db_episode = db_episode_dict[episode_key]

                playlist_videos_dict[db_playlist].append(db_episode)

            elif plex_video.type == "movie":
                movie_key = (plex_video.title, plex_video.year, plex_video.duration)
                if movie_key not in db_movie_dict:
                    db_movie = Movie(
                        title=plex_video.title,
                        year=plex_video.year,
                        duration=plex_video.duration,
                    )
                    db_movie_dict[movie_key] = db_movie
                else:
                    db_movie = db_movie_dict[movie_key]

                playlist_videos_dict[db_playlist].append(db_movie)
        for db_video in remove_db_videos:
            remove_item_dict[db_playlist].append(db_video)

    except Exception as e:
        LOGGER.error("An error occurred in update_video_playlist.", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e


def _update_remove_playlists(playlists_to_remove, db_playlist_dict):
    try:
        for playlist in playlists_to_remove:
            LOGGER.info(f"Removing playlist: {playlist} from the database")
            db_playlist = db_playlist_dict[playlist]
            db.session.delete(db_playlist)
    except Exception as e:
        LOGGER.error("An error occurred while removing playlists.", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e


def _update_playlist_duration(db_playlist, plex_playlists):
    try:
        plex_playlist = next(
            (playlist for playlist in plex_playlists if playlist.title == db_playlist.title), None
        )
        if plex_playlist:
            db_playlist.duration = plex_playlist.duration
            db.session.add(db_playlist)
            db.session.commit()
        else:
            LOGGER.warning(f"Skipping playlist: {db_playlist.title} (not found on Plex server)")
    except Exception as e:
        LOGGER.error("Error in update_playlist_duration", exc_info=True)
        traceback.print_exc()
        db.session.rollback()
        raise e
