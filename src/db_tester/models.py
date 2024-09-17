from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db

playlist_track = Table(
    "playlist_track",
    db.metadata,
    Column("playlist_id", Integer, ForeignKey("playlists.id"), primary_key=True),
    Column("track_id", Integer, ForeignKey("tracks.id"), primary_key=True),
)


class Playlist(db.Model):
    __tablename__ = "playlists"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    tracks: Mapped[List["Track"]] = relationship(
        "Track", secondary=playlist_track, back_populates="playlists", lazy="dynamic"
    )


class Track(db.Model):
    __tablename__ = "tracks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    track_number: Mapped[int] = mapped_column(Integer, nullable=False)
    album_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    artist_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    playlists: Mapped[List[Playlist]] = relationship(
        "Playlist", secondary=playlist_track, back_populates="tracks", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Track(title={self.title}, track_number={self.track_number}, album_title={self.album_title}, artist_name={self.artist_name})>"
