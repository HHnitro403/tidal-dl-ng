"""Track data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Track:
    """Track metadata model."""

    id: Optional[int] = None
    playlist_id: str = ""
    track_id: str = ""
    title: str = ""
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[int] = None  # Duration in seconds
    tidal_url: str = ""
    added_at: Optional[datetime] = None  # When added to playlist on TIDAL
    discovered_at: Optional[datetime] = None  # When discovered by monitor
