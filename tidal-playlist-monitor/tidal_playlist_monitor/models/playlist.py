"""Playlist data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Playlist:
    """Playlist metadata model."""

    playlist_id: str
    name: str
    description: Optional[str] = None
    owner: Optional[str] = None
    last_checked: Optional[datetime] = None
    track_count: int = 0
    enabled: bool = True
    created_at: Optional[datetime] = None
