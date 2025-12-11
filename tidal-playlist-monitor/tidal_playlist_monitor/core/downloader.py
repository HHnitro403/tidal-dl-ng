"""Download manager with Windows compatibility."""

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from ..config.database import DatabaseHandler
from ..models.download import DownloadStatus
from ..models.track import Track


class TidalDownloader:
    """Manages downloads using tidal-dl-ng with Windows compatibility."""

    def __init__(
        self,
        db: DatabaseHandler,
        logger: logging.Logger,
        quality: str = "HI_RES",
        download_path: Optional[Path] = None,
        skip_existing: bool = True,
        max_retries: int = 3,
        retry_delay: int = 60,
        delay_between_downloads: int = 5,
        timeout: int = 600
    ):
        """Initialize downloader.

        Args:
            db: Database handler
            logger: Logger instance
            quality: Audio quality (LOW, HIGH, LOSSLESS, HI_RES)
            download_path: Base download directory
            skip_existing: Skip already downloaded tracks
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
            delay_between_downloads: Delay between sequential downloads
            timeout: Timeout per track in seconds
        """
        self.db = db
        self.logger = logger
        self.quality = quality
        self.download_path = download_path
        self.skip_existing = skip_existing
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.delay_between_downloads = delay_between_downloads
        self.timeout = timeout

    def _get_subprocess_kwargs(self) -> dict:
        """Get subprocess kwargs with Windows compatibility.

        Returns:
            Dictionary of kwargs for subprocess.run
        """
        kwargs = {
            'capture_output': True,
            'text': True,
            'timeout': self.timeout
        }

        # Windows-specific: hide subprocess window
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            kwargs['startupinfo'] = startupinfo
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        return kwargs

    def run_tidal_command(
        self,
        args: List[str],
        timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess:
        """Run a tidal-dl-ng command.

        Args:
            args: Command arguments (e.g., ['dl', 'URL'])
            timeout: Optional timeout override

        Returns:
            CompletedProcess result

        Raises:
            subprocess.TimeoutExpired: If command times out
            subprocess.SubprocessError: If command fails
        """
        cmd = ['tidal-dl-ng'] + args

        kwargs = self._get_subprocess_kwargs()
        if timeout:
            kwargs['timeout'] = timeout

        try:
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, **kwargs)
            return result

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timed out after {kwargs['timeout']}s: {' '.join(cmd)}")
            raise

        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            raise

    def ensure_authenticated(self) -> bool:
        """Ensure tidal-dl-ng is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        try:
            # Try to run a simple command to check authentication
            result = self.run_tidal_command(['cfg', 'quality_audio'], timeout=10)

            if result.returncode == 0:
                self.logger.debug("tidal-dl-ng is authenticated")
                return True
            else:
                self.logger.error("tidal-dl-ng not authenticated")
                return False

        except Exception as e:
            self.logger.error(f"Failed to check authentication: {e}")
            return False

    def configure_quality(self) -> None:
        """Configure download quality in tidal-dl-ng."""
        try:
            self.logger.info(f"Setting download quality to {self.quality}")

            # Map quality to tidal-dl-ng format
            quality_map = {
                'LOW': 'low_320k',
                'HIGH': 'high_lossless',
                'LOSSLESS': 'high_lossless',
                'HI_RES': 'hi_res'
            }

            tidal_quality = quality_map.get(self.quality, 'hi_res')

            # Set quality
            result = self.run_tidal_command(['cfg', 'quality_audio', tidal_quality], timeout=10)

            if result.returncode != 0:
                self.logger.warning(f"Failed to set quality: {result.stderr}")

            # Disable FLAC extraction on Windows to avoid terminal flash
            if sys.platform == 'win32':
                self.logger.debug("Disabling FLAC extraction on Windows")
                result = self.run_tidal_command(['cfg', 'extract_flac', 'false'], timeout=10)

                if result.returncode != 0:
                    self.logger.warning(f"Failed to disable FLAC extraction: {result.stderr}")

            # Set download path if specified
            if self.download_path:
                self.logger.debug(f"Setting download path to {self.download_path}")
                result = self.run_tidal_command(
                    ['cfg', 'download_base_path', str(self.download_path)],
                    timeout=10
                )

                if result.returncode != 0:
                    self.logger.warning(f"Failed to set download path: {result.stderr}")

            # Set skip existing
            skip_value = 'true' if self.skip_existing else 'false'
            result = self.run_tidal_command(['cfg', 'skip_existing', skip_value], timeout=10)

            if result.returncode != 0:
                self.logger.warning(f"Failed to set skip_existing: {result.stderr}")

        except Exception as e:
            self.logger.error(f"Failed to configure tidal-dl-ng: {e}")

    def download_track(
        self,
        track: Track,
        retry_count: int = 0
    ) -> bool:
        """Download a single track.

        Args:
            track: Track to download
            retry_count: Current retry count

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(
                f"Downloading: {track.artist} - {track.title} (ID: {track.track_id})"
            )

            # Create download record
            self.db.create_download(track.track_id)
            self.db.update_download_status(track.track_id, DownloadStatus.DOWNLOADING)

            # Run download
            result = self.run_tidal_command(['dl', track.tidal_url])

            if result.returncode == 0:
                self.logger.info(f"Successfully downloaded: {track.title}")
                self.db.update_download_status(track.track_id, DownloadStatus.COMPLETED)
                return True
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                self.logger.error(f"Download failed for {track.title}: {error_msg}")
                self.db.update_download_status(
                    track.track_id,
                    DownloadStatus.FAILED,
                    error_msg[:500]  # Limit error message length
                )
                return False

        except subprocess.TimeoutExpired:
            error_msg = f"Download timed out after {self.timeout}s"
            self.logger.error(f"{error_msg}: {track.title}")
            self.db.update_download_status(track.track_id, DownloadStatus.FAILED, error_msg)
            return False

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Download error for {track.title}: {error_msg}")
            self.db.update_download_status(
                track.track_id,
                DownloadStatus.FAILED,
                error_msg[:500]
            )
            return False

    def download_batch(
        self,
        tracks: List[Track],
        delay_between: Optional[int] = None
    ) -> dict[str, int]:
        """Download multiple tracks with delays.

        Args:
            tracks: List of tracks to download
            delay_between: Optional delay override (in seconds)

        Returns:
            Dictionary with success/failure counts
        """
        if not tracks:
            return {'success': 0, 'failed': 0}

        delay = delay_between if delay_between is not None else self.delay_between_downloads

        results = {'success': 0, 'failed': 0}

        for i, track in enumerate(tracks):
            success = self.download_track(track)

            if success:
                results['success'] += 1
            else:
                results['failed'] += 1

            # Add delay between downloads (except after last track)
            if i < len(tracks) - 1 and delay > 0:
                self.logger.debug(f"Waiting {delay}s before next download...")
                time.sleep(delay)

        self.logger.info(
            f"Batch download complete: {results['success']} successful, "
            f"{results['failed']} failed"
        )

        return results

    def retry_failed_downloads(self) -> dict[str, int]:
        """Retry failed downloads.

        Returns:
            Dictionary with retry statistics
        """
        failed_downloads = self.db.get_failed_downloads()

        if not failed_downloads:
            self.logger.info("No failed downloads to retry")
            return {'retried': 0, 'success': 0, 'failed': 0}

        self.logger.info(f"Retrying {len(failed_downloads)} failed download(s)")

        stats = {'retried': 0, 'success': 0, 'failed': 0}

        for download in failed_downloads:
            # Check if max retries exceeded
            if download.retry_count >= self.max_retries:
                self.logger.warning(
                    f"Max retries exceeded for track {download.track_id}, skipping"
                )
                continue

            # Increment retry count
            self.db.increment_retry_count(download.track_id)
            self.db.update_download_status(download.track_id, DownloadStatus.RETRYING)

            stats['retried'] += 1

            # Wait before retry
            if self.retry_delay > 0:
                self.logger.debug(f"Waiting {self.retry_delay}s before retry...")
                time.sleep(self.retry_delay)

            # Get track info
            track = self.db.get_track_by_id(download.track_id)
            if not track:
                self.logger.error(f"Track {download.track_id} not found in database")
                continue

            # Retry download
            success = self.download_track(track, retry_count=download.retry_count + 1)

            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1

        self.logger.info(
            f"Retry complete: {stats['success']} successful, {stats['failed']} failed"
        )

        return stats
