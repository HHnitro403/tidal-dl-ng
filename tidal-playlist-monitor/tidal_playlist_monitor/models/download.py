"""Download status models."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class DownloadStatus(str, Enum):
    """Download status enumeration."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Download:
    """Download record model."""

    id: Optional[int] = None
    track_id: str = ""
    status: DownloadStatus = DownloadStatus.PENDING
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Convert status to enum if it's a string."""
        if isinstance(self.status, str):
            self.status = DownloadStatus(self.status)
