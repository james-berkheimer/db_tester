from ..extensions import db
from ..models import Episode, Movie, Photo, Playlist, Track
from ..plex import get_server, plex_exceptions


def get_add_remove_playlists(db_playlists, plex_playlists):
    # plex_server = get_server()
    add_playlists = []
    remove_playlists = []

    db_playlist_titles = {db_playlist.title for db_playlist in db_playlists}
    # plex_playlists = plex_server.playlists()
    plex_playlist_titles = {plex_playlist.title for plex_playlist in plex_playlists}

    if not db_playlist_titles:
        add_playlists = list(plex_playlist_titles)
    elif not plex_playlist_titles:
        remove_playlists = list(db_playlist_titles)
    else:
        add_playlists = list(plex_playlist_titles - db_playlist_titles)
        remove_playlists = list(db_playlist_titles - plex_playlist_titles)

    return add_playlists, remove_playlists


def get_out_of_date_playlists(db_playlists):
    plex_server = get_server()
    out_of_date_playlists = []
    for db_playlist in db_playlists:
        try:
            plex_playlist = plex_server.playlist(db_playlist.title)
            if db_playlist.playlist_type == "audio":
                if (
                    db_playlist.tracks.count() != len(plex_playlist.items())
                    or db_playlist.duration != plex_playlist.duration
                ):
                    out_of_date_playlists.append(db_playlist)
            elif db_playlist.playlist_type == "video":
                video_count = db_playlist.episodes.count() + db_playlist.movies.count()
                if (
                    video_count != len(plex_playlist.items())
                    or db_playlist.duration != plex_playlist.duration
                ):
                    out_of_date_playlists.append(db_playlist)
            elif db_playlist.playlist_type == "photo":
                if db_playlist.photos.count() != len(plex_playlist.items()):
                    out_of_date_playlists.append(db_playlist)
        except plex_exceptions.NotFound:
            print(f"Skipping playlist: {db_playlist.title} (not found on Plex server)")
    return out_of_date_playlists


def parse_audio_playlist(db_playliat_dict, db_tracks_dict, playlist_tracks_dict, plex_playlist):
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
    db_playliat_dict,
    db_episode_titles,
    db_movie_titles,
    playlist_videos_dict,
    plex_playlist,
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

            playlist_videos_dict[db_playlist].append(db_episode)
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

            playlist_videos_dict[db_playlist].append(db_movie)


def parse_photo_playlist(db_playliat_dict, db_photo_titles, playlist_photos_dict, plex_playlist):
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
        db.session.query(Photo).filter(Photo.playlists.any(id=db_playlist.id)).delete(
            synchronize_session=False
        )

    plex_photos = plex_playlist.items()
    playlist_photos_dict[db_playlist] = []

    for plex_photo in plex_photos:
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

        playlist_photos_dict[db_playlist].append(db_photo)
