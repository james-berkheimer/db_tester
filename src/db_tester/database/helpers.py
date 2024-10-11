import logging

# from ..app import app
from ..plex import plex_exceptions

logger = logging.getLogger("app_logger")


def get_playlists_to_add_and_remove(db_playlists, plex_playlists):
    db_playlist_titles = {db_playlist.title for db_playlist in db_playlists}
    plex_playlist_titles = {plex_playlist.title for plex_playlist in plex_playlists}

    add_playlists = plex_playlist_titles - db_playlist_titles
    remove_playlists = db_playlist_titles - plex_playlist_titles

    return add_playlists, remove_playlists


def get_out_of_date_data(db_playlists, plex_playlists):
    logger.info("Starting to check for out-of-date playlists.")
    out_of_date_data = {}
    plex_playlist_dict = {pl.title: pl for pl in plex_playlists}

    for db_playlist in db_playlists:
        try:
            plex_playlist = plex_playlist_dict.get(db_playlist.title)
            if not plex_playlist:
                continue

            plex_playlist_items = plex_playlist.items()
            plex_playlist_items_len = len(plex_playlist_items)
            db_playlist_duration = db_playlist.duration

            if db_playlist.playlist_type == "audio":
                db_tracks_count = db_playlist.tracks.count()
                if (
                    db_tracks_count != plex_playlist_items_len
                    or db_playlist_duration != plex_playlist.duration
                ):
                    add_remove = _get_add_remove_playlist_items(db_playlist, plex_playlist_items)
                    out_of_date_data[db_playlist] = add_remove
                    logger.debug(f"Audio playlist '{db_playlist.title}' needs update: {add_remove}")

            elif db_playlist.playlist_type == "video":
                db_episodes_count = db_playlist.episodes.count()
                db_movies_count = db_playlist.movies.count()
                video_count = db_episodes_count + db_movies_count
                if (
                    video_count != plex_playlist_items_len
                    or db_playlist_duration != plex_playlist.duration
                ):
                    add_remove = _get_add_remove_playlist_items(db_playlist, plex_playlist_items)
                    out_of_date_data[db_playlist] = add_remove
                    logger.debug(f"Video playlist '{db_playlist.title}' needs update: {add_remove}")

            elif db_playlist.playlist_type == "photo":
                db_photos_count = db_playlist.photos.count()
                if db_photos_count != plex_playlist_items_len:
                    add_remove = _get_add_remove_playlist_items(db_playlist, plex_playlist_items)
                    out_of_date_data[db_playlist] = add_remove
                    logger.debug(f"Photo playlist '{db_playlist.title}' needs update: {add_remove}")

        except plex_exceptions.NotFound:
            logger.error(f"Skipping playlist: {db_playlist.title} (not found on Plex server)")

    logger.info(f"Total out-of-date playlists: {len(out_of_date_data)}")
    return out_of_date_data


def __get_add_remove_playlist_items(db_playlist, plex_playlist_items):
    if db_playlist.playlist_type == "audio":
        db_track_titles = {track.title for track in db_playlist.tracks}
        plex_track_titles = {track.title for track in plex_playlist_items}
        add_tracks = [track for track in plex_playlist_items if track.title not in db_track_titles]
        remove_tracks = [track for track in db_playlist.tracks if track.title not in plex_track_titles]
        return add_tracks, remove_tracks

    elif db_playlist.playlist_type == "video":
        db_episode_keys = {
            (episode.title, episode.season_number, episode.show_title)
            for episode in db_playlist.episodes
        }
        db_movie_keys = {(movie.title, movie.year) for movie in db_playlist.movies}
        add_videos = []

        for plex_video in plex_playlist_items:
            if plex_video.type == "episode":
                episode_key = (plex_video.title, plex_video.season().index, plex_video.show().title)
                if episode_key not in db_episode_keys:
                    add_videos.append(plex_video)
                else:
                    db_episode_keys.remove(episode_key)
            elif plex_video.type == "movie":
                movie_key = (plex_video.title, plex_video.year)
                if movie_key not in db_movie_keys:
                    add_videos.append(plex_video)
                else:
                    db_movie_keys.remove(movie_key)

        remove_episodes = [
            episode
            for episode in db_playlist.episodes
            if (episode.title, episode.season_number, episode.show_title) in db_episode_keys
        ]
        remove_movies = [
            movie for movie in db_playlist.movies if (movie.title, movie.year) in db_movie_keys
        ]
        return add_videos, (remove_episodes + remove_movies)

    elif db_playlist.playlist_type == "photo":
        db_photo_titles = {photo.title for photo in db_playlist.photos}
        plex_photo_titles = {photo.title for photo in plex_playlist_items}
        add_photos = [photo for photo in plex_playlist_items if photo.title not in db_photo_titles]
        remove_photos = [photo for photo in db_playlist.photos if photo.title not in plex_photo_titles]
        return add_photos, remove_photos


def _get_add_remove_playlist_items(db_playlist, plex_playlist_items):
    if db_playlist.playlist_type == "audio":
        db_track_titles = {track.title for track in db_playlist.tracks}
        add_tracks = [track for track in plex_playlist_items if track.title not in db_track_titles]
        remove_tracks = [
            track
            for track in db_playlist.tracks
            if track.title not in {track.title for track in plex_playlist_items}
        ]
        return add_tracks, remove_tracks

    elif db_playlist.playlist_type == "video":
        db_episode_keys, db_movie_keys = db_playlist.get_indexed_titles()
        add_videos = []

        for plex_video in plex_playlist_items:
            if plex_video.type == "episode":
                episode_key = (plex_video.title, plex_video.season().index, plex_video.show().title)
                if episode_key not in db_episode_keys:
                    add_videos.append(plex_video)
                else:
                    db_episode_keys.remove(episode_key)
            elif plex_video.type == "movie":
                movie_key = (plex_video.title, plex_video.year)
                if movie_key not in db_movie_keys:
                    add_videos.append(plex_video)
                else:
                    db_movie_keys.remove(movie_key)

        remove_episodes = [
            episode
            for episode in db_playlist.episodes
            if (episode.title, episode.season_number, episode.show_title) in db_episode_keys
        ]
        remove_movies = [
            movie for movie in db_playlist.movies if (movie.title, movie.year) in db_movie_keys
        ]
        return add_videos, remove_episodes + remove_movies

    elif db_playlist.playlist_type == "photo":
        db_photo_titles = {photo.title for photo in db_playlist.photos}
        add_photos = [photo for photo in plex_playlist_items if photo.title not in db_photo_titles]
        remove_photos = [
            photo
            for photo in db_playlist.photos
            if photo.title not in {photo.title for photo in plex_playlist_items}
        ]
        return add_photos, remove_photos
