from ..plex import plex_exceptions
from ..utils.logging import LOGGER


def get_playlists_to_add_and_remove(db_playlists, plex_playlists):
    add_playlists = []
    remove_playlists = []

    db_playlist_titles = {db_playlist.title for db_playlist in db_playlists}
    plex_playlist_titles = {plex_playlist.title for plex_playlist in plex_playlists}

    if not db_playlist_titles:
        add_playlists = list(plex_playlist_titles)
    elif not plex_playlist_titles:
        remove_playlists = list(db_playlist_titles)
    else:
        add_playlists = list(plex_playlist_titles - db_playlist_titles)
        remove_playlists = list(db_playlist_titles - plex_playlist_titles)

    return add_playlists, remove_playlists


def get_out_of_date_data(db_playlists, plex_playlists):
    out_of_date_data = {}
    plex_playlist_dict = {pl.title: pl for pl in plex_playlists}

    for db_playlist in db_playlists:
        try:
            plex_playlist = plex_playlist_dict.get(db_playlist.title)
            if not plex_playlist:
                continue

            plex_items = plex_playlist.items()
            if db_playlist.playlist_type == "audio":
                if (
                    db_playlist.tracks.count() != len(plex_items)
                    or db_playlist.duration != plex_playlist.duration
                ):
                    add_remove = _get_add_remove_playlist_items(db_playlist, plex_items)
                    out_of_date_data[db_playlist] = add_remove
            elif db_playlist.playlist_type == "video":
                video_count = db_playlist.episodes.count() + db_playlist.movies.count()
                if video_count != len(plex_items) or db_playlist.duration != plex_playlist.duration:
                    add_remove = _get_add_remove_playlist_items(db_playlist, plex_items)
                    out_of_date_data[db_playlist] = add_remove
            elif db_playlist.playlist_type == "photo":
                if db_playlist.photos.count() != len(plex_items):
                    add_remove = _get_add_remove_playlist_items(db_playlist, plex_items)
                    out_of_date_data[db_playlist] = add_remove
        except plex_exceptions.NotFound:
            LOGGER.error(f"Skipping playlist: {db_playlist.title} (not found on Plex server)")
    return out_of_date_data


def _get_add_remove_playlist_items(db_playlist, plex_items):
    if db_playlist.playlist_type == "audio":
        db_tracks = list(db_playlist.tracks)
        db_track_titles = {track.title for track in db_tracks}
        plex_track_titles = {track.title for track in plex_items}
        add_tracks = [track for track in plex_items if track.title not in db_track_titles]
        remove_tracks = [track for track in db_tracks if track.title not in plex_track_titles]
        return add_tracks, remove_tracks

    elif db_playlist.playlist_type == "video":
        db_episodes = list(db_playlist.episodes)
        db_movies = list(db_playlist.movies)
        db_episode_keys = {
            (episode.title, episode.season_number, episode.show_title) for episode in db_episodes
        }
        db_movie_keys = {(movie.title, movie.year) for movie in db_movies}
        add_videos = []

        for plex_video in plex_items:
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
            for episode in db_episodes
            if (episode.title, episode.season_number, episode.show_title) in db_episode_keys
        ]
        remove_movies = [movie for movie in db_movies if (movie.title, movie.year) in db_movie_keys]
        return add_videos, (remove_episodes + remove_movies)

    elif db_playlist.playlist_type == "photo":
        db_photos = list(db_playlist.photos)
        db_photo_titles = {photo.title for photo in db_photos}
        plex_photo_titles = {photo.title for photo in plex_items}
        add_photos = [photo for photo in plex_items if photo.title not in db_photo_titles]
        remove_photos = [photo for photo in db_photos if photo.title not in plex_photo_titles]
        return add_photos, remove_photos
