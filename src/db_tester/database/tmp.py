from ..extensions import db
from ..models import Episode, Movie, Photo, Playlist, Track


def process_audio_playlist_refresh(
    db_playliat_dict, db_tracks_dict, playlist_tracks_dict, plex_playlist
):
    # Check if the playlist title from Plex exists in the database dictionary
    if plex_playlist.title not in db_playliat_dict:
        # If not, create a new Playlist object and add it to the dictionary
        db_playlist = Playlist(
            title=plex_playlist.title,
            playlist_type=plex_playlist.playlistType,
            duration=plex_playlist.duration,
            thumbnail=plex_playlist.thumb,
        )
        db_playliat_dict[plex_playlist.title] = db_playlist
        existing_tracks = set()
    else:
        # If it exists, retrieve the existing Playlist object
        db_playlist = db_playliat_dict[plex_playlist.title]
        # Get the current set of tracks associated with the playlist
        existing_tracks = set(db_playlist.tracks)

    # Initialize a set to store new tracks from the Plex playlist
    new_tracks = set()

    # Iterate over each track in the Plex playlist
    for plex_track in plex_playlist.items():
        # Retrieve album and artist information for the track
        plex_album = plex_track.album()
        plex_artist = plex_track.artist()
        # Create a unique key for the track based on its title, track number, album title, and artist name
        track_key = (plex_track.title, plex_track.trackNumber, plex_album.title, plex_artist.title)
        if track_key not in db_tracks_dict:
            # If the track is not in the database dictionary, create a new Track object and add it to the dictionary
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
            # TODO is this required?
            # If it exists, retrieve the existing Track object
            db_track = db_tracks_dict[track_key]

        # Add the track to the set of new tracks
        new_tracks.add(db_track)

    # Determine which tracks need to be added and which need to be removed
    tracks_to_add = new_tracks - existing_tracks
    tracks_to_remove = existing_tracks - new_tracks

    # Add new tracks to the playlist
    for track in tracks_to_add:
        db_playlist.tracks.append(track)

    # Remove old tracks from the playlist
    for track in tracks_to_remove:
        db_playlist.tracks.remove(track)

    # Update the playlist_tracks_dict with the new set of tracks
    playlist_tracks_dict[db_playlist] = list(new_tracks)

    # Add the updated playlist to the session for committing to the database
    db.session.add(db_playlist)


def process_video_playlist_refresh(
    db_playliat_dict, db_episode_titles, db_movie_titles, playlist_videos_dict, plex_playlist
):
    if plex_playlist.title not in db_playliat_dict:
        db_playlist = Playlist(
            title=plex_playlist.title,
            playlist_type=plex_playlist.playlistType,
            duration=plex_playlist.duration,
            thumbnail=plex_playlist.thumb,
        )
        db_playliat_dict[plex_playlist.title] = db_playlist
    else:
        db_playlist = db_playliat_dict[plex_playlist.title]

    existing_episodes = set(db_playlist.episodes)
    existing_movies = set(db_playlist.movies)
    new_episodes = set()
    new_movies = set()

    for plex_video in plex_playlist.items():
        if plex_video.type == "episode":
            plex_show = plex_video.show()
            plex_season = plex_video.season()
            episode_key = (plex_video.title, plex_video.index, plex_season.index, plex_show.title)
            if episode_key not in db_episode_titles:
                db_episode = Episode(
                    title=plex_video.title,
                    episode_number=plex_video.index,
                    duration=plex_video.duration,
                    season_number=plex_season.index,
                    show_title=plex_show.title,
                    show_year=plex_show.year,
                )
                db_episode_titles[episode_key] = db_episode
            else:
                db_episode = db_episode_titles[episode_key]

            new_episodes.add(db_episode)
        elif plex_video.type == "movie":
            movie_key = (plex_video.title, plex_video.year, plex_video.duration)
            if movie_key not in db_movie_titles:
                db_movie = Movie(
                    title=plex_video.title,
                    year=plex_video.year,
                    duration=plex_video.duration,
                    thumbnail=plex_video.thumb,
                )
                db_movie_titles[movie_key] = db_movie
            else:
                db_movie = db_movie_titles[movie_key]

            new_movies.add(db_movie)

    episodes_to_add = new_episodes - existing_episodes
    episodes_to_remove = existing_episodes - new_episodes
    movies_to_add = new_movies - existing_movies
    movies_to_remove = existing_movies - new_movies

    for episode in episodes_to_add:
        db_playlist.episodes.append(episode)

    for episode in episodes_to_remove:
        db_playlist.episodes.remove(episode)

    for movie in movies_to_add:
        db_playlist.movies.append(movie)

    for movie in movies_to_remove:
        db_playlist.movies.remove(movie)

    playlist_videos_dict[db_playlist] = list(new_episodes) + list(new_movies)

    db.session.add(db_playlist)


def process_photo_playlist_refresh(
    db_playliat_dict, db_photo_titles, playlist_photos_dict, plex_playlist
):
    if plex_playlist.title not in db_playliat_dict:
        db_playlist = Playlist(
            title=plex_playlist.title,
            playlist_type=plex_playlist.playlistType,
            duration=plex_playlist.duration,
            thumbnail=plex_playlist.thumb,
        )
        db_playliat_dict[plex_playlist.title] = db_playlist
    else:
        db_playlist = db_playliat_dict[plex_playlist.title]

    existing_photos = set(db_playlist.photos)
    new_photos = set()

    for plex_photo in plex_playlist.items():
        photo_key = (plex_photo.title, plex_photo.thumb)
        if photo_key not in db_photo_titles:
            db_photo = Photo(
                title=plex_photo.title,
                thumbnail=plex_photo.thumb,
                file=plex_photo.media[0].parts[0].file,
            )
            db_photo_titles[photo_key] = db_photo
        else:
            db_photo = db_photo_titles[photo_key]

        new_photos.add(db_photo)

    to_add = new_photos - existing_photos
    to_remove = existing_photos - new_photos

    for photo in to_add:
        db_playlist.photos.append(photo)

    for photo in to_remove:
        db_playlist.photos.remove(photo)

    playlist_photos_dict[db_playlist] = list(new_photos)

    db.session.add(db_playlist)


def _parse_data(db_playlists, plex_playlists):
    try:
        db_tracks = db.session.query(Track).all()
        db_episodes = db.session.query(Episode).all()
        db_movies = db.session.query(Movie).all()
        db_photos = db.session.query(Photo).all()

        db_playlist_dict = {db_playlist.title: db_playlist for db_playlist in db_playlists}
        db_tracks_dict = {
            (track.title, track.track_number, track.album_title, track.artist_name): track
            for track in db_tracks
        }
        db_episode_titles = {
            (episode.title, episode.index, episode.season().index, episode.show().title): episode
            for episode in db_episodes
        }
        db_movie_titles = {(movie.title, movie.year, movie.duration): movie for movie in db_movies}
        db_photo_titles = {(photo.title, photo.thumb): photo for photo in db_photos}

        for plex_playlist in plex_playlists:
            if plex_playlist.playlistType == "audio":
                parse_audio_playlist(
                    db_playlist_dict, db_tracks_dict, playlist_tracks_dict, plex_playlist
                )
            elif plex_playlist.playlistType == "video":
                parse_video_playlist(
                    db_playlist_dict,
                    db_episode_titles,
                    db_movie_titles,
                    playlist_videos_dict,
                    plex_playlist,
                )
            elif plex_playlist.playlistType == "photo":
                parse_photo_playlist(
                    db_playlist_dict,
                    db_photo_titles,
                    playlist_photos_dict,
                    plex_playlist,
                )
            else:
                print(f"Skipping playlist: {plex_playlist.title}")
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        raise e
