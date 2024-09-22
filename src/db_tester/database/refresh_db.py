from ..extensions import db, session, socketio
from ..models import Playlist
from ..plex import get_server
from .helpers import parse_audio_playlist, parse_photo_playlist, parse_video_playlist


def emit_log_message(message):
    socketio.emit("log_message", {"message": message})


def _get_out_of_date_playlists():
    plex_server = get_server()
    db_playlists = session.query(Playlist).all()
    out_of_date_playlists = {"audio": [], "video": [], "photo": []}
    for db_playlist in db_playlists:
        plex_playlist = plex_server.playlist(db_playlist.title)
        if db_playlist.playlist_type == "audio":
            if (
                db_playlist.tracks.count() != len(plex_playlist.items())
                or db_playlist.duration != plex_playlist.duration
            ):
                out_of_date_playlists["audio"].append(db_playlist)
        elif db_playlist.playlist_type == "video":
            video_count = db_playlist.episodes.count() + db_playlist.movies.count()
            if (
                video_count != len(plex_playlist.items())
                or db_playlist.duration != plex_playlist.duration
            ):
                out_of_date_playlists["video"].append(db_playlist)
        elif db_playlist.playlist_type == "photo":
            if db_playlist.photos.count() != len(plex_playlist.items()):
                out_of_date_playlists["photo"].append(db_playlist)
    return out_of_date_playlists


def _get_add_remove_playlists():
    plex_server = get_server()
    db_playlists = session.query(Playlist).all()
    add_playlists = []
    remove_playlists = []

    db_playlist_titles = {db_playlist.title for db_playlist in db_playlists}
    plex_playlists = plex_server.playlists()
    plex_playlist_titles = {plex_playlist.title for plex_playlist in plex_playlists}

    if not db_playlist_titles:
        add_playlists = list(plex_playlist_titles)
    elif not plex_playlist_titles:
        remove_playlists = list(db_playlist_titles)
    else:
        add_playlists = list(plex_playlist_titles - db_playlist_titles)
        remove_playlists = list(db_playlist_titles - plex_playlist_titles)

    return add_playlists, remove_playlists


def refresh_db():
    playlists_to_refresh = _get_out_of_date_playlists()
    if all(not db_playlists for db_playlists in playlists_to_refresh.values()):
        emit_log_message("No playlists to refresh")
    else:
        db_playlist_titles = {}
        db_track_titles = {}
        db_episode_titles = {}
        db_movie_titles = {}
        db_photo_titles = {}
        playlist_tracks_dict = {}
        playlist_videos_dict = {}
        playlist_photos_dict = {}

        plex_server = get_server()

        for playlist_type, db_playlists in playlists_to_refresh.items():
            for db_playlist in db_playlists:
                emit_log_message(f"Refreshing playlist: {db_playlist.title}")
                plex_playlist = plex_server.playlist(db_playlist.title)
                if playlist_type == "audio":
                    parse_audio_playlist(
                        db_playlist_titles, db_track_titles, playlist_tracks_dict, plex_playlist
                    )
                elif playlist_type == "video":
                    parse_video_playlist(
                        db_playlist_titles,
                        db_episode_titles,
                        db_movie_titles,
                        playlist_videos_dict,
                        plex_playlist,
                    )
                elif playlist_type == "photo":
                    parse_photo_playlist(
                        db_playlist_titles, db_photo_titles, playlist_photos_dict, plex_playlist
                    )
                else:
                    emit_log_message(f"Unknown playlist type: {playlist_type}")
                emit_log_message(f"Refreshed playlist: {db_playlist.title}")

        # Commit all changes to the database
        emit_log_message("Commiting changes to the database")
        db.session.commit()
