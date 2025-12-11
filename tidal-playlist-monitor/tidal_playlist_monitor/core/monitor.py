"""Playlist monitoring and change detection."""

import logging
from datetime import datetime
from typing import List, Set

import tidalapi

from ..config.database import DatabaseHandler
from ..models.track import Track


class PlaylistMonitor:
    """Monitors TIDAL playlists for changes."""

    def __init__(
        self,
        session: tidalapi.Session,
        db: DatabaseHandler,
        logger: logging.Logger
    ):
        """Initialize playlist monitor.

        Args:
            session: TIDAL API session
            db: Database handler
            logger: Logger instance
        """
        self.session = session
        self.db = db
        self.logger = logger

    def get_playlist(self, playlist_id: str) -> tidalapi.Playlist:
        """Get playlist from TIDAL.

        Args:
            playlist_id: TIDAL playlist ID

        Returns:
            Playlist object

        Raises:
            Exception: If playlist cannot be fetched
        """
        try:
            playlist = self.session.playlist(playlist_id)
            if not playlist:
                raise ValueError(f"Playlist {playlist_id} not found")
            return playlist
        except Exception as e:
            self.logger.error(f"Failed to fetch playlist {playlist_id}: {e}")
            raise

    def get_playlist_tracks(self, playlist: tidalapi.Playlist) -> List[Track]:
        """Get all tracks from a playlist.

        Args:
            playlist: TIDAL playlist object

        Returns:
            List of Track objects
        """
        tracks = []

        try:
            # Iterate through all tracks (handles pagination automatically)
            for tidal_track in playlist.tracks():
                # Skip if not a track (could be video)
                if not isinstance(tidal_track, tidalapi.Track):
                    continue

                # Extract track metadata
                track = Track(
                    track_id=str(tidal_track.id),
                    title=tidal_track.name,
                    artist=tidal_track.artist.name if tidal_track.artist else None,
                    album=tidal_track.album.name if tidal_track.album else None,
                    duration=tidal_track.duration,
                    tidal_url=f"https://tidal.com/browse/track/{tidal_track.id}",
                    added_at=getattr(tidal_track, 'user_date_added', None),
                    discovered_at=datetime.now()
                )
                tracks.append(track)

        except Exception as e:
            self.logger.error(f"Error fetching tracks from playlist {playlist.id}: {e}")
            raise

        return tracks

    def detect_new_tracks(
        self,
        playlist_id: str,
        current_tracks: List[Track]
    ) -> List[Track]:
        """Detect new tracks by comparing with stored tracks.

        Args:
            playlist_id: Playlist ID
            current_tracks: Current tracks from TIDAL

        Returns:
            List of new Track objects
        """
        # Get stored track IDs from database
        stored_track_ids = self.db.get_playlist_track_ids(playlist_id)

        # Find new tracks
        current_track_ids = {track.track_id for track in current_tracks}
        new_track_ids = current_track_ids - stored_track_ids

        # Filter to get new Track objects
        new_tracks = [track for track in current_tracks if track.track_id in new_track_ids]

        if new_tracks:
            self.logger.info(
                f"Found {len(new_tracks)} new track(s) in playlist {playlist_id}"
            )
        else:
            self.logger.debug(f"No new tracks found in playlist {playlist_id}")

        return new_tracks

    def update_playlist_state(
        self,
        playlist_id: str,
        tracks: List[Track]
    ) -> None:
        """Update the stored state of a playlist.

        Args:
            playlist_id: Playlist ID
            tracks: Current tracks
        """
        try:
            self.db.update_playlist_tracks(playlist_id, tracks)
            self.db.update_playlist_last_checked(playlist_id, datetime.now())
            self.logger.debug(f"Updated state for playlist {playlist_id}")
        except Exception as e:
            self.logger.error(f"Failed to update playlist state: {e}")
            raise

    def check_playlist(self, playlist_id: str) -> List[Track]:
        """Check a playlist for new tracks.

        This is the main method that orchestrates the monitoring process:
        1. Fetch current tracks from TIDAL
        2. Compare with stored tracks
        3. Detect new tracks
        4. Update stored state

        Args:
            playlist_id: Playlist ID to check

        Returns:
            List of new tracks found (empty if none)

        Raises:
            Exception: If check fails
        """
        try:
            self.logger.info(f"Checking playlist {playlist_id} for changes...")

            # Get playlist from TIDAL
            playlist = self.get_playlist(playlist_id)

            # Get all current tracks
            current_tracks = self.get_playlist_tracks(playlist)
            self.logger.debug(f"Fetched {len(current_tracks)} tracks from TIDAL")

            # Detect new tracks
            new_tracks = self.detect_new_tracks(playlist_id, current_tracks)

            # Update stored state
            self.update_playlist_state(playlist_id, current_tracks)

            return new_tracks

        except Exception as e:
            self.logger.error(f"Failed to check playlist {playlist_id}: {e}")
            # Re-raise to let scheduler handle retry logic
            raise

    def check_all_playlists(self) -> dict[str, List[Track]]:
        """Check all monitored playlists for new tracks.

        Returns:
            Dictionary mapping playlist_id to list of new tracks
        """
        results = {}
        playlists = self.db.get_monitored_playlists(enabled_only=True)

        self.logger.info(f"Checking {len(playlists)} playlist(s) for changes")

        for playlist in playlists:
            try:
                new_tracks = self.check_playlist(playlist.playlist_id)
                results[playlist.playlist_id] = new_tracks
            except Exception as e:
                self.logger.error(
                    f"Failed to check playlist {playlist.playlist_id} ({playlist.name}): {e}"
                )
                results[playlist.playlist_id] = []
                # Continue checking other playlists

        return results
