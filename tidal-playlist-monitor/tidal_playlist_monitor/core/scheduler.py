"""Scheduler for periodic playlist checks."""

import logging
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


class PlaylistScheduler:
    """Manages scheduled playlist checks."""

    def __init__(
        self,
        logger: logging.Logger,
        check_function: Callable,
        check_interval_minutes: int = 30,
        use_cron: bool = False,
        cron_schedule: str = "0 */2 * * *"
    ):
        """Initialize scheduler.

        Args:
            logger: Logger instance
            check_function: Function to call for checks (should take no args)
            check_interval_minutes: Check interval in minutes (if not using cron)
            use_cron: Whether to use cron-style scheduling
            cron_schedule: Cron schedule string (if use_cron is True)
        """
        self.logger = logger
        self.check_function = check_function
        self.check_interval_minutes = check_interval_minutes
        self.use_cron = use_cron
        self.cron_schedule = cron_schedule

        self.scheduler = BackgroundScheduler()
        self._job_id = "playlist_check"

    def start(self) -> None:
        """Start the scheduler."""
        try:
            # Add the job
            if self.use_cron:
                trigger = CronTrigger.from_crontab(self.cron_schedule)
                self.logger.info(f"Starting scheduler with cron schedule: {self.cron_schedule}")
            else:
                trigger = IntervalTrigger(minutes=self.check_interval_minutes)
                self.logger.info(
                    f"Starting scheduler with interval: {self.check_interval_minutes} minutes"
                )

            self.scheduler.add_job(
                self._safe_check_function,
                trigger=trigger,
                id=self._job_id,
                name="Playlist Check",
                replace_existing=True
            )

            # Start the scheduler
            self.scheduler.start()
            self.logger.info("Scheduler started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            raise

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        try:
            if self.scheduler.running:
                self.logger.info("Stopping scheduler...")
                self.scheduler.shutdown(wait=True)
                self.logger.info("Scheduler stopped")
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}")

    def _safe_check_function(self) -> None:
        """Wrapper for check function with error handling.

        This ensures that errors in the check function don't stop the scheduler.
        """
        try:
            self.logger.debug("Running scheduled playlist check")
            self.check_function()
        except Exception as e:
            self.logger.error(f"Error in scheduled check: {e}", exc_info=True)
            # Don't re-raise - we want the scheduler to continue

    def trigger_immediate_check(self) -> None:
        """Trigger an immediate check (outside of schedule).

        This runs the check function in the scheduler's thread pool.
        """
        try:
            self.logger.info("Triggering immediate check")
            self.scheduler.add_job(
                self._safe_check_function,
                id="manual_check",
                replace_existing=True
            )
        except Exception as e:
            self.logger.error(f"Failed to trigger immediate check: {e}")

    def get_next_run_time(self) -> Optional[str]:
        """Get the next scheduled run time.

        Returns:
            Next run time as string, or None if scheduler not running
        """
        try:
            job = self.scheduler.get_job(self._job_id)
            if job and job.next_run_time:
                return str(job.next_run_time)
            return None
        except Exception:
            return None

    def is_running(self) -> bool:
        """Check if scheduler is running.

        Returns:
            True if running
        """
        return self.scheduler.running
