"""Main background service for TIDAL Playlist Monitor."""

import signal
import sys
import time
from pathlib import Path
from typing import Optional

import tidalapi

from .config.database import DatabaseHandler
from .config.settings import Settings
from .core.downloader import TidalDownloader
from .core.monitor import PlaylistMonitor
from .core.notifier import Notifier
from .core.scheduler import PlaylistScheduler
from .utils.logger import setup_logger
from .utils.platform import is_windows


class TidalPlaylistService:
    """Main service for monitoring playlists and downloading tracks."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the service.

        Args:
            config_path: Path to configuration file (optional)
        """
        self.running = False
        self.config_path = config_path

        # Load settings
        self.settings = Settings.from_file_or_default(config_path)

        # Setup logging
        self.logger = setup_logger(
            log_file=self.settings.logging.path,
            level=self.settings.logging.level,
            max_size_mb=self.settings.logging.max_size_mb,
            backup_count=self.settings.logging.backup_count,
            console=True
        )

        self.logger.info("Initializing TIDAL Playlist Monitor service")

        # Initialize components
        self.db = DatabaseHandler(self.settings.database.path)
        self.session: Optional[tidalapi.Session] = None
        self.monitor: Optional[PlaylistMonitor] = None
        self.downloader: Optional[TidalDownloader] = None
        self.notifier: Optional[Notifier] = None
        self.scheduler: Optional[PlaylistScheduler] = None

    def init_tidal_session(self) -> None:
        """Initialize and authenticate TIDAL session."""
        self.logger.info("Initializing TIDAL session")

        self.session = tidalapi.Session()
        token_path = self.settings.tidal.token_path

        # Try to load existing token
        if token_path and token_path.exists():
            try:
                import json
                with open(token_path, 'r') as f:
                    token_data = json.load(f)

                # Load the session with token data
                self.session.load_oauth_session(
                    token_data.get('token_type'),
                    token_data.get('access_token'),
                    token_data.get('refresh_token'),
                    token_data.get('expiry_time')
                )

                if self.session.check_login():
                    self.logger.info("Loaded existing TIDAL session")
                    return
            except Exception as e:
                self.logger.warning(f"Failed to load existing token: {e}")

        # Need to authenticate
        self.logger.warning("TIDAL authentication required")
        self.logger.info("Please visit the URL shown below and log in:")

        self.session.login_oauth_simple()

        # Save token manually
        if token_path:
            token_path.parent.mkdir(parents=True, exist_ok=True)

            import json
            token_data = {
                'token_type': self.session.token_type,
                'access_token': self.session.access_token,
                'refresh_token': self.session.refresh_token,
                'expiry_time': self.session.expiry_time.timestamp() if hasattr(self.session.expiry_time, 'timestamp') else self.session.expiry_time
            }

            with open(token_path, 'w') as f:
                json.dump(token_data, f, indent=2)

            self.logger.info(f"Token saved to {token_path}")

    def check_and_download(self) -> None:
        """Main job: check playlists and download new tracks."""
        try:
            self.logger.info("=== Starting scheduled playlist check ===")

            # Check all playlists
            results = self.monitor.check_all_playlists()

            # Collect all new tracks
            all_new_tracks = []
            for playlist_id, new_tracks in results.items():
                if new_tracks:
                    playlist = self.db.get_playlist(playlist_id)
                    playlist_name = playlist.name if playlist else playlist_id

                    self.logger.info(
                        f"Found {len(new_tracks)} new track(s) in '{playlist_name}'"
                    )

                    # Send notification
                    if self.settings.notifications.on_new_tracks:
                        self.notifier.notify_new_tracks(len(new_tracks), playlist_name)

                    all_new_tracks.extend(new_tracks)

            if not all_new_tracks:
                self.logger.info("No new tracks found")
                return

            # Download new tracks
            self.logger.info(f"Starting download of {len(all_new_tracks)} track(s)")

            download_results = self.downloader.download_batch(all_new_tracks)

            # Send completion notification
            if self.settings.notifications.on_download_complete:
                self.notifier.notify_download_complete(
                    download_results['success'],
                    download_results['failed']
                )

            self.logger.info("=== Scheduled check complete ===")

        except Exception as e:
            self.logger.error(f"Error in check_and_download: {e}", exc_info=True)

            # Send error notification if enabled
            if self.settings.notifications.on_error:
                self.notifier.notify_error(str(e))

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown()

        # Windows uses SIGBREAK, Linux/macOS use SIGTERM
        signal.signal(signal.SIGINT, signal_handler)

        if is_windows():
            signal.signal(signal.SIGBREAK, signal_handler)
        else:
            signal.signal(signal.SIGTERM, signal_handler)

    def start(self) -> None:
        """Start the monitoring service."""
        try:
            self.running = True

            # Setup signal handlers
            self.setup_signal_handlers()

            # Initialize TIDAL session
            self.init_tidal_session()

            if not self.session or not self.session.check_login():
                self.logger.error("TIDAL authentication failed")
                raise RuntimeError("TIDAL authentication required")

            # Initialize components
            self.monitor = PlaylistMonitor(self.session, self.db, self.logger)

            self.downloader = TidalDownloader(
                db=self.db,
                logger=self.logger,
                quality=self.settings.download.audio_quality,
                download_path=self.settings.download.download_path,
                skip_existing=self.settings.download.skip_existing,
                max_retries=self.settings.download.max_retries,
                retry_delay=self.settings.download.retry_delay,
                delay_between_downloads=self.settings.download.delay_between_downloads
            )

            self.notifier = Notifier(
                logger=self.logger,
                enabled=self.settings.notifications.enabled
            )

            # Configure downloader
            self.logger.info("Configuring tidal-dl-ng")
            self.downloader.configure_quality()

            # Check authentication
            if not self.downloader.ensure_authenticated():
                self.logger.error("tidal-dl-ng not authenticated")
                self.logger.info("Please run: tidal-dl-ng login")
                raise RuntimeError("tidal-dl-ng authentication required")

            # Create scheduler
            self.scheduler = PlaylistScheduler(
                logger=self.logger,
                check_function=self.check_and_download,
                check_interval_minutes=self.settings.scheduler.check_interval_minutes,
                use_cron=self.settings.scheduler.use_cron_schedule,
                cron_schedule=self.settings.scheduler.cron_schedule
            )

            # Start scheduler
            self.scheduler.start()

            next_run = self.scheduler.get_next_run_time()
            if next_run:
                self.logger.info(f"Next check scheduled for: {next_run}")

            self.logger.info("Service started successfully")
            self.logger.info("Press Ctrl+C to stop")

            # Run initial check
            self.logger.info("Running initial check...")
            self.check_and_download()

            # Keep service alive
            self._keep_alive()

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
            self.shutdown()
        except Exception as e:
            self.logger.error(f"Service error: {e}", exc_info=True)
            self.shutdown()
            raise

    def _keep_alive(self) -> None:
        """Keep the service alive.

        Windows doesn't support signal.pause(), so we use a sleep loop.
        """
        if is_windows():
            # Windows: use while loop with sleep
            while self.running:
                time.sleep(1)
        else:
            # Linux/macOS: use signal.pause()
            while self.running:
                signal.pause()

    def shutdown(self) -> None:
        """Graceful shutdown."""
        if not self.running:
            return

        self.logger.info("Shutting down service...")
        self.running = False

        # Stop scheduler
        if self.scheduler:
            self.scheduler.stop()

        self.logger.info("Service stopped")

        # Exit
        sys.exit(0)


def main():
    """Main entry point."""
    service = TidalPlaylistService()
    service.start()


if __name__ == "__main__":
    main()
