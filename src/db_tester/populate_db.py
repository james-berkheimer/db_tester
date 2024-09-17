import traceback

from .extensions import db
from .models import Playlist, Track
from .plex.server import get_server


def populate_db():
    try:
        server = get_server()
        playlists = server.playlists()
        for playlist in playlists:
            # print(f"Processing playlist: {playlist.title}")
            if playlist.playlistType == "audio":
                tracks = playlist.items()
                db_playlist = db.session.query(Playlist).filter_by(title=playlist.title).first()
                if not db_playlist:
                    db_playlist = Playlist(title=playlist.title)
                    db.session.add(db_playlist)
                else:
                    # Delete existing tracks if updating
                    db.session.query(Track).filter(Track.playlists.any(id=db_playlist.id)).delete(
                        synchronize_session=False
                    )

                for track in tracks:
                    album = track.album()
                    artist = track.artist()
                    # print(
                    #     f"Adding track: ({track.trackNumber}) {track.title}: {album.title} - {artist.title}"
                    # )
                    db_track = (
                        db.session.query(Track)
                        .filter_by(
                            title=track.title,
                            track_number=track.trackNumber,
                            album_title=album.title,
                            artist_title=artist.title,
                        )
                        .first()
                    )

                    if not db_track:
                        db_track = Track(
                            title=track.title,
                            track_number=track.trackNumber,
                            album_title=album.title,
                            artist_title=artist.title,
                        )
                        db.session.add(db_track)

                    if db_track not in db_playlist.tracks:
                        db_playlist.tracks.append(db_track)

        db.session.commit()

    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        raise e
