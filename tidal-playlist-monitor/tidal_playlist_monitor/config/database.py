"""Database management for TIDAL Playlist Monitor."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..models.download import Download, DownloadStatus
from ..models.playlist import Playlist
from ..models.track import Track


class DatabaseHandler:
    """SQLite database handler for playlist monitoring."""

    def __init__(self, db_path: Path):
        """Initialize database handler.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_database(self) -> None:
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create playlists table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    playlist_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner TEXT,
                    last_checked TIMESTAMP,
                    track_count INTEGER DEFAULT 0,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create tracks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id TEXT NOT NULL,
                    track_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    artist TEXT,
                    album TEXT,
                    duration INTEGER,
                    tidal_url TEXT NOT NULL,
                    added_at TIMESTAMP,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_id),
                    UNIQUE(playlist_id, track_id)
                )
            """)

            # Create downloads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (track_id) REFERENCES tracks(track_id)
                )
            """)

            # Create config table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_playlist ON tracks(playlist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_track_id ON tracks(track_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_track_id ON downloads(track_id)")

    # Playlist methods

    def add_playlist(self, playlist: Playlist) -> None:
        """Add a playlist to monitoring.

        Args:
            playlist: Playlist to add
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO playlists
                (playlist_id, name, description, owner, track_count, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                playlist.playlist_id,
                playlist.name,
                playlist.description,
                playlist.owner,
                playlist.track_count,
                playlist.enabled,
                playlist.created_at or datetime.now()
            ))

    def remove_playlist(self, playlist_id: str) -> None:
        """Remove a playlist from monitoring.

        Args:
            playlist_id: Playlist ID to remove
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Remove playlist (tracks will be cascade deleted by foreign key)
            cursor.execute("DELETE FROM playlists WHERE playlist_id = ?", (playlist_id,))

    def get_monitored_playlists(self, enabled_only: bool = True) -> List[Playlist]:
        """Get all monitored playlists.

        Args:
            enabled_only: Only return enabled playlists

        Returns:
            List of Playlist objects
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM playlists"
            if enabled_only:
                query += " WHERE enabled = 1"

            cursor.execute(query)
            rows = cursor.fetchall()

            return [
                Playlist(
                    playlist_id=row['playlist_id'],
                    name=row['name'],
                    description=row['description'],
                    owner=row['owner'],
                    last_checked=datetime.fromisoformat(row['last_checked']) if row['last_checked'] else None,
                    track_count=row['track_count'],
                    enabled=bool(row['enabled']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                )
                for row in rows
            ]

    def get_playlist(self, playlist_id: str) -> Optional[Playlist]:
        """Get a specific playlist.

        Args:
            playlist_id: Playlist ID

        Returns:
            Playlist object or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM playlists WHERE playlist_id = ?", (playlist_id,))
            row = cursor.fetchone()

            if row:
                return Playlist(
                    playlist_id=row['playlist_id'],
                    name=row['name'],
                    description=row['description'],
                    owner=row['owner'],
                    last_checked=datetime.fromisoformat(row['last_checked']) if row['last_checked'] else None,
                    track_count=row['track_count'],
                    enabled=bool(row['enabled']),
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                )
            return None

    def update_playlist_last_checked(self, playlist_id: str, timestamp: datetime) -> None:
        """Update playlist last checked timestamp.

        Args:
            playlist_id: Playlist ID
            timestamp: Last checked timestamp
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE playlists SET last_checked = ? WHERE playlist_id = ?",
                (timestamp.isoformat(), playlist_id)
            )

    def enable_playlist(self, playlist_id: str, enabled: bool = True) -> None:
        """Enable or disable playlist monitoring.

        Args:
            playlist_id: Playlist ID
            enabled: Whether to enable or disable
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE playlists SET enabled = ? WHERE playlist_id = ?",
                (enabled, playlist_id)
            )

    # Track methods

    def get_playlist_track_ids(self, playlist_id: str) -> Set[str]:
        """Get all track IDs for a playlist.

        Args:
            playlist_id: Playlist ID

        Returns:
            Set of track IDs
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT track_id FROM tracks WHERE playlist_id = ?",
                (playlist_id,)
            )
            return {row['track_id'] for row in cursor.fetchall()}

    def add_track(self, track: Track) -> None:
        """Add a track to the database.

        Args:
            track: Track to add
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO tracks
                (playlist_id, track_id, title, artist, album, duration, tidal_url, added_at, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                track.playlist_id,
                track.track_id,
                track.title,
                track.artist,
                track.album,
                track.duration,
                track.tidal_url,
                track.added_at.isoformat() if track.added_at else None,
                track.discovered_at or datetime.now()
            ))

    def update_playlist_tracks(self, playlist_id: str, tracks: List[Track]) -> None:
        """Update all tracks for a playlist.

        Args:
            playlist_id: Playlist ID
            tracks: List of tracks
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Add all tracks
            for track in tracks:
                track.playlist_id = playlist_id
                cursor.execute("""
                    INSERT OR IGNORE INTO tracks
                    (playlist_id, track_id, title, artist, album, duration, tidal_url, added_at, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    track.playlist_id,
                    track.track_id,
                    track.title,
                    track.artist,
                    track.album,
                    track.duration,
                    track.tidal_url,
                    track.added_at.isoformat() if track.added_at else None,
                    track.discovered_at or datetime.now()
                ))

            # Update track count
            cursor.execute(
                "UPDATE playlists SET track_count = ? WHERE playlist_id = ?",
                (len(tracks), playlist_id)
            )

    def get_track_by_id(self, track_id: str) -> Optional[Track]:
        """Get a track by its TIDAL ID.

        Args:
            track_id: TIDAL track ID

        Returns:
            Track object or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tracks WHERE track_id = ? LIMIT 1", (track_id,))
            row = cursor.fetchone()

            if row:
                return Track(
                    id=row['id'],
                    playlist_id=row['playlist_id'],
                    track_id=row['track_id'],
                    title=row['title'],
                    artist=row['artist'],
                    album=row['album'],
                    duration=row['duration'],
                    tidal_url=row['tidal_url'],
                    added_at=datetime.fromisoformat(row['added_at']) if row['added_at'] else None,
                    discovered_at=datetime.fromisoformat(row['discovered_at']) if row['discovered_at'] else None
                )
            return None

    # Download methods

    def create_download(self, track_id: str) -> int:
        """Create a new download record.

        Args:
            track_id: TIDAL track ID

        Returns:
            Download ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO downloads (track_id, status, started_at)
                VALUES (?, ?, ?)
            """, (track_id, DownloadStatus.PENDING.value, datetime.now()))
            return cursor.lastrowid

    def update_download_status(
        self,
        track_id: str,
        status: DownloadStatus,
        error_msg: Optional[str] = None
    ) -> None:
        """Update download status.

        Args:
            track_id: TIDAL track ID
            status: New status
            error_msg: Error message (if failed)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            completed_at = datetime.now() if status == DownloadStatus.COMPLETED else None

            cursor.execute("""
                UPDATE downloads
                SET status = ?, error_message = ?, completed_at = ?
                WHERE track_id = ? AND status != ?
            """, (
                status.value,
                error_msg,
                completed_at,
                track_id,
                DownloadStatus.COMPLETED.value
            ))

    def increment_retry_count(self, track_id: str) -> int:
        """Increment retry count for a download.

        Args:
            track_id: TIDAL track ID

        Returns:
            New retry count
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE downloads
                SET retry_count = retry_count + 1
                WHERE track_id = ?
            """, (track_id,))

            cursor.execute("SELECT retry_count FROM downloads WHERE track_id = ?", (track_id,))
            row = cursor.fetchone()
            return row['retry_count'] if row else 0

    def get_failed_downloads(self) -> List[Download]:
        """Get all failed downloads.

        Returns:
            List of Download objects
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM downloads
                WHERE status = ?
                ORDER BY started_at DESC
            """, (DownloadStatus.FAILED.value,))

            rows = cursor.fetchall()
            return [
                Download(
                    id=row['id'],
                    track_id=row['track_id'],
                    status=DownloadStatus(row['status']),
                    retry_count=row['retry_count'],
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    error_message=row['error_message']
                )
                for row in rows
            ]

    def get_download_stats(self) -> Dict[str, int]:
        """Get download statistics.

        Returns:
            Dictionary with download counts by status
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM downloads
                GROUP BY status
            """)

            stats = {status.value: 0 for status in DownloadStatus}
            for row in cursor.fetchall():
                stats[row['status']] = row['count']

            return stats
