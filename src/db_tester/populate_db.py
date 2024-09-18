import traceback

from .extensions import db
from .models import Episode, Movie, Photo, Playlist, Track
from .plex.server import get_server


def process_audio_playlist(db_playlist_titles, db_track_titles, playlist_tracks_dict, playlist):
    if playlist.title not in db_playlist_titles:
        db_playlist = Playlist(
            title=playlist.title,
            playlist_type=playlist.playlistType,
            duration=playlist.duration,
            thumbnail=playlist.thumb,
        )
        db_playlist_titles[playlist.title] = db_playlist
    else:
        db_playlist = db_playlist_titles[playlist.title]
        db.session.query(Track).filter(Track.playlists.any(id=db_playlist.id)).delete(
            synchronize_session=False
        )

    tracks = playlist.items()
    playlist_tracks_dict[db_playlist] = []

    for track in tracks:
        album = track.album()
        artist = track.artist()
        track_key = (track.title, track.trackNumber, album.title, artist.title)
        if track_key not in db_track_titles:
            db_track = Track(
                title=track.title,
                track_number=track.trackNumber,
                duration=track.duration,
                album_title=album.title,
                album_year=album.year,
                artist_name=artist.title,
            )
            db_track_titles[track_key] = db_track
        else:
            db_track = db_track_titles[track_key]

        playlist_tracks_dict[db_playlist].append(db_track)


def process_video_playlist(
    db_playlist_titles,
    db_episode_titles,
    db_movie_titles,
    playlist_videos_dict,
    playlist,
):
    if playlist.title not in db_playlist_titles:
        db_playlist = Playlist(
            title=playlist.title,
            playlist_type=playlist.playlistType,
            duration=playlist.duration,
            thumbnail=playlist.thumb,
        )
        db_playlist_titles[playlist.title] = db_playlist
    else:
        db_playlist = db_playlist_titles[playlist.title]
        db.session.query(Episode).filter(Episode.playlists.any(id=db_playlist.id)).delete(
            synchronize_session=False
        )

    videos = playlist.items()
    playlist_videos_dict[db_playlist] = []

    for video in videos:
        if video.type == "episode":
            show = video.show()
            season = video.season()
            episode_key = (video.title, video.index, season.index, show.title)
            if episode_key not in db_episode_titles:
                db_episode = Episode(
                    title=video.title,
                    episode_number=video.index,
                    duration=video.duration,
                    season_number=season.index,
                    show_title=show.title,
                    show_year=show.year,
                )
                db_episode_titles[episode_key] = db_episode
            else:
                db_episode = db_episode_titles[episode_key]

            playlist_videos_dict[db_playlist].append(db_episode)
        elif video.type == "movie":
            movie_key = (video.title, video.year, video.duration)
            if movie_key not in db_movie_titles:
                db_movie = Movie(
                    title=video.title,
                    year=video.year,
                    duration=video.duration,
                    thumbnail=video.thumb,
                )
                db_movie_titles[movie_key] = db_movie
            else:
                db_movie = db_movie_titles[movie_key]

            playlist_videos_dict[db_playlist].append(db_movie)


def process_photo_playlist(db_playlist_titles, db_photo_titles, playlist_photos_dict, playlist):
    if playlist.title not in db_playlist_titles:
        db_playlist = Playlist(
            title=playlist.title,
            playlist_type=playlist.playlistType,
            duration=playlist.duration,
            thumbnail=playlist.thumb,
        )
        db_playlist_titles[playlist.title] = db_playlist
    else:
        db_playlist = db_playlist_titles[playlist.title]
        db.session.query(Photo).filter(Photo.playlists.any(id=db_playlist.id)).delete(
            synchronize_session=False
        )

    photos = playlist.items()
    playlist_photos_dict[db_playlist] = []

    for photo in photos:
        photo_key = (photo.title, photo.thumb)
        if photo_key not in db_photo_titles:
            db_photo = Photo(
                title=photo.title,
                thumbnail=photo.thumb,
                file=photo.media[0].parts[0].file,
            )
            db_photo_titles[photo_key] = db_photo
        else:
            db_photo = db_photo_titles[photo_key]

        playlist_photos_dict[db_playlist].append(db_photo)


def populate_db_bulk_add():
    try:
        server = get_server()
        playlists = server.playlists()
        db_playlists = db.session.query(Playlist).all()
        db_tracks = db.session.query(Track).all()
        db_episodes = db.session.query(Episode).all()
        db_movies = db.session.query(Movie).all()
        db_photos = db.session.query(Photo).all()

        db_playlist_titles = {playlist.title: playlist for playlist in db_playlists}
        db_track_titles = {
            (track.title, track.track_number, track.album_title, track.artist_title): track
            for track in db_tracks
        }
        db_episode_titles = {
            (video.title, video.index, video.season().index, video.show().title): video
            for video in db_episodes
        }
        db_movie_titles = {(movie.title, movie.year, movie.duration): movie for movie in db_movies}
        db_photo_titles = {(photo.title, photo.thumb): photo for photo in db_photos}

        playlist_tracks_dict = {}
        playlist_videos_dict = {}
        playlist_photos_dict = {}

        for playlist in playlists:
            if playlist.playlistType == "audio":
                process_audio_playlist(
                    db_playlist_titles, db_track_titles, playlist_tracks_dict, playlist
                )
            if playlist.playlistType == "video":
                process_video_playlist(
                    db_playlist_titles,
                    db_episode_titles,
                    db_movie_titles,
                    playlist_videos_dict,
                    playlist,
                )
            if playlist.playlistType == "photo":
                process_photo_playlist(
                    db_playlist_titles,
                    db_photo_titles,
                    playlist_photos_dict,
                    playlist,
                )

        # Commit new playlists to the database
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

        # Associate tracks with playlists and commit new tracks to the database
        for db_playlist, tracks in playlist_tracks_dict.items():
            db_playlist = db_playlists[db_playlist.title]  # Ensure we use the managed instance
            for db_track in tracks:
                if db_track not in db_playlist.tracks:
                    db_playlist.tracks.append(db_track)
            db.session.add(db_playlist)  # Explicitly add the playlist to the session

        # Associate episodes and movies with playlists and commit new episodes to the database
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

        for db_playlist, photos in playlist_photos_dict.items():
            db_playlist = db_playlists[db_playlist.title]
            for db_photo in photos:
                if db_photo not in db_playlist.photos:
                    db_playlist.photos.append(db_photo)
            db.session.add(db_playlist)

        print(f"Adding {len(db_track_titles)} tracks to the database")
        db.session.bulk_save_objects(list(db_track_titles.values()))
        print(f"Adding {len(db_episode_titles)} episodes to the database")
        db.session.bulk_save_objects(list(db_episode_titles.values()))
        print(f"Adding {len(db_movie_titles)} movies to the database")
        db.session.bulk_save_objects(list(db_movie_titles.values()))
        print(f"Adding {len(db_photo_titles)} photos to the database")
        db.session.bulk_save_objects(list(db_photo_titles.values()))
        db.session.commit()

    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        raise e
