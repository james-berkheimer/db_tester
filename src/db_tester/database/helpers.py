import traceback

from ..extensions import db
from ..models import Episode, Movie, Photo, Playlist, Track
from ..plex import plex_exceptions


def get_add_remove_playlists(db_playlists, plex_playlists):
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
    for db_playlist in db_playlists:
        try:
            plex_playlist = next((pl for pl in plex_playlists if pl.title == db_playlist.title), None)
            if not plex_playlist:
                continue
            if db_playlist.playlist_type == "audio":
                if (
                    db_playlist.tracks.count() != len(plex_playlist.items())
                    or db_playlist.duration != plex_playlist.duration
                ):
                    add_remove = get_add_remove_playlist_items(db_playlist, plex_playlist)
                    out_of_date_data[db_playlist] = add_remove
            elif db_playlist.playlist_type == "video":
                video_count = db_playlist.episodes.count() + db_playlist.movies.count()
                if (
                    video_count != len(plex_playlist.items())
                    or db_playlist.duration != plex_playlist.duration
                ):
                    add_remove = get_add_remove_playlist_items(db_playlist, plex_playlist)
                    out_of_date_data[db_playlist] = add_remove
            elif db_playlist.playlist_type == "photo":
                if db_playlist.photos.count() != len(plex_playlist.items()):
                    add_remove = get_add_remove_playlist_items(db_playlist, plex_playlist)
                    out_of_date_data[db_playlist] = add_remove
        except plex_exceptions.NotFound:
            print(f"Skipping playlist: {db_playlist.title} (not found on Plex server)")
    return out_of_date_data


def get_add_remove_playlist_items(db_playlist, plex_playlist):
    if db_playlist.playlist_type == "audio":
        db_tracks = list(db_playlist.tracks)
        plex_tracks = list(plex_playlist.items())
        db_track_titles = {track.title for track in db_tracks}
        plex_track_titles = {track.title for track in plex_tracks}
        add_tracks = [track for track in plex_tracks if track.title not in db_track_titles]
        remove_tracks = [track for track in db_tracks if track.title not in plex_track_titles]
        return add_tracks, remove_tracks

    elif db_playlist.playlist_type == "video":
        db_episodes = list(db_playlist.episodes)
        db_movies = list(db_playlist.movies)
        plex_videos = list(plex_playlist.items())
        db_episode_keys = {
            (episode.title, episode.season_number, episode.show_title) for episode in db_episodes
        }
        db_movie_keys = {(movie.title, movie.year) for movie in db_movies}
        add_videos = []

        for plex_video in plex_videos:
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
        plex_photos = list(plex_playlist.items())
        db_photo_titles = {photo.title for photo in db_photos}
        plex_photo_titles = {photo.title for photo in plex_photos}
        add_photos = [photo for photo in plex_photos if photo.title not in db_photo_titles]
        remove_photos = [photo for photo in db_photos if photo.title not in plex_photo_titles]
        return add_photos, remove_photos


def parse_audio_playlist(db_playlist_dict, db_tracks_dict, playlist_tracks_dict, plex_playlist):
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
        db.session.query(Track).filter(Track.playlists.any(id=db_playlist.id)).delete(
            synchronize_session=False
        )

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


def parse_video_playlist(
    db_playlist_dict,
    db_episode_dict,
    db_movies_dict,
    playlist_videos_dict,
    plex_playlist,
):
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
        db.session.query(Episode).filter(Episode.playlists.any(id=db_playlist.id)).delete(
            synchronize_session=False
        )

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


def parse_photo_playlist(db_playlist_dict, db_photo_dict, playlist_photos_dict, plex_playlist):
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
        db.session.query(Photo).filter(Photo.playlists.any(id=db_playlist.id)).delete(
            synchronize_session=False
        )

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


def parse_playlists(
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
):
    try:
        if playlists_to_add:
            for plex_playlist_title in playlists_to_add:
                plex_playlist = next(
                    (pl for pl in plex_playlists if pl.title == plex_playlist_title), None
                )
                if plex_playlist.playlistType == "audio":
                    parse_audio_playlist(
                        db_playlist_dict, db_tracks_dict, playlist_tracks_dict, plex_playlist
                    )
                elif plex_playlist.playlistType == "video":
                    parse_video_playlist(
                        db_playlist_dict,
                        db_episode_dict,
                        db_movie_dict,
                        playlist_videos_dict,
                        plex_playlist,
                    )
                elif plex_playlist.playlistType == "photo":
                    parse_photo_playlist(
                        db_playlist_dict,
                        db_photo_dict,
                        playlist_photos_dict,
                        plex_playlist,
                    )
                else:
                    print(f"Skipping playlist: {plex_playlist.title}")
        else:
            print("No playlists to add")

    except Exception as e:
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
        for db_playlist, add_remove_items in update_data.items():
            remove_item_dict[db_playlist] = []
            playlist_tracks_dict[db_playlist] = []
            if db_playlist.playlist_type == "audio":
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

            elif db_playlist.playlist_type == "video":
                print(f"db_playlist: {db_playlist.title}")
                print(f"playlist_videos_dict keys: {playlist_videos_dict.keys()}")
                playlist_videos_dict[db_playlist] = []
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

            elif db_playlist.playlist_type == "photo":
                playlist_photos_dict[db_playlist] = []
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

            else:
                print(f"Skipping playlist: {db_playlist.title}")

            # Updating the playlist duration
            plex_playlist = next((pl for pl in plex_playlists if pl.title == db_playlist.title), None)
            if plex_playlist:
                db_playlist.duration = plex_playlist.duration
                db.session.add(db_playlist)
                db.session.commit()
            else:
                print(f"Skipping playlist: {db_playlist.title} (not found on Plex server)")

    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        raise e
