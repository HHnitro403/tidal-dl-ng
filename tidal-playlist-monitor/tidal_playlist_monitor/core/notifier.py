"""Cross-platform notification system."""

import logging
import sys
from typing import Optional

try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

# Windows-specific notification support
if sys.platform == 'win32':
    try:
        from winotify import Notification as WinNotification
        WINOTIFY_AVAILABLE = True
    except ImportError:
        WINOTIFY_AVAILABLE = False
else:
    WINOTIFY_AVAILABLE = False


class Notifier:
    """Cross-platform desktop notification handler."""

    def __init__(
        self,
        logger: logging.Logger,
        enabled: bool = True,
        app_name: str = "TIDAL Playlist Monitor"
    ):
        """Initialize notifier.

        Args:
            logger: Logger instance
            enabled: Whether notifications are enabled
            app_name: Application name for notifications
        """
        self.logger = logger
        self.enabled = enabled
        self.app_name = app_name

        # Check which notification backend is available
        self.backend = self._detect_backend()

        if not self.backend and self.enabled:
            self.logger.warning("No notification backend available, notifications disabled")
            self.enabled = False

    def _detect_backend(self) -> Optional[str]:
        """Detect available notification backend.

        Returns:
            Backend name ('winotify', 'plyer', or None)
        """
        if sys.platform == 'win32' and WINOTIFY_AVAILABLE:
            self.logger.debug("Using winotify for notifications")
            return 'winotify'
        elif PLYER_AVAILABLE:
            self.logger.debug("Using plyer for notifications")
            return 'plyer'
        else:
            self.logger.debug("No notification backend available")
            return None

    def send(
        self,
        title: str,
        message: str,
        duration: int = 5
    ) -> bool:
        """Send a desktop notification.

        Args:
            title: Notification title
            message: Notification message
            duration: Duration in seconds (ignored on some platforms)

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            if self.backend == 'winotify':
                return self._send_winotify(title, message)
            elif self.backend == 'plyer':
                return self._send_plyer(title, message, duration)
            else:
                return False

        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            return False

    def _send_winotify(self, title: str, message: str) -> bool:
        """Send notification using winotify (Windows 10/11).

        Args:
            title: Notification title
            message: Notification message

        Returns:
            True if successful
        """
        try:
            toast = WinNotification(
                app_id=self.app_name,
                title=title,
                msg=message,
                duration="short"
            )
            toast.show()
            self.logger.debug(f"Notification sent: {title}")
            return True

        except Exception as e:
            self.logger.error(f"winotify failed: {e}")
            return False

    def _send_plyer(
        self,
        title: str,
        message: str,
        duration: int
    ) -> bool:
        """Send notification using plyer (cross-platform).

        Args:
            title: Notification title
            message: Notification message
            duration: Duration in seconds

        Returns:
            True if successful
        """
        try:
            plyer_notification.notify(
                title=title,
                message=message,
                app_name=self.app_name,
                timeout=duration
            )
            self.logger.debug(f"Notification sent: {title}")
            return True

        except Exception as e:
            self.logger.error(f"plyer failed: {e}")
            return False

    def notify_new_tracks(self, count: int, playlist_name: str) -> bool:
        """Notify about new tracks found.

        Args:
            count: Number of new tracks
            playlist_name: Playlist name

        Returns:
            True if notification sent
        """
        return self.send(
            title="New Tracks Found",
            message=f"Found {count} new track(s) in '{playlist_name}'"
        )

    def notify_download_complete(
        self,
        success_count: int,
        failed_count: int
    ) -> bool:
        """Notify about completed downloads.

        Args:
            success_count: Number of successful downloads
            failed_count: Number of failed downloads

        Returns:
            True if notification sent
        """
        if failed_count > 0:
            message = (
                f"Downloaded {success_count} track(s), "
                f"{failed_count} failed"
            )
        else:
            message = f"Successfully downloaded {success_count} track(s)"

        return self.send(
            title="Downloads Complete",
            message=message
        )

    def notify_error(self, error_message: str) -> bool:
        """Notify about an error.

        Args:
            error_message: Error description

        Returns:
            True if notification sent
        """
        return self.send(
            title="Monitor Error",
            message=error_message
        )
