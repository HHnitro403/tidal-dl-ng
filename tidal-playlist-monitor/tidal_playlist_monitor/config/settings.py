"""Configuration management for TIDAL Playlist Monitor."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from ..utils.platform import get_config_dir, get_default_download_dir


@dataclass
class TidalConfig:
    """TIDAL authentication configuration."""

    token_path: Optional[Path] = None

    def __post_init__(self):
        """Set default token path if not specified."""
        if self.token_path is None:
            self.token_path = get_config_dir() / 'tidal_token.json'
        elif isinstance(self.token_path, str):
            self.token_path = Path(self.token_path).expanduser()


@dataclass
class DatabaseConfig:
    """Database configuration."""

    path: Optional[Path] = None

    def __post_init__(self):
        """Set default database path if not specified."""
        if self.path is None:
            self.path = get_config_dir() / 'monitor.db'
        elif isinstance(self.path, str):
            self.path = Path(self.path).expanduser()


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""

    check_interval_minutes: int = 30
    use_cron_schedule: bool = False
    cron_schedule: str = "0 */2 * * *"

    def __post_init__(self):
        """Validate configuration."""
        if self.check_interval_minutes < 5:
            raise ValueError("check_interval_minutes must be >= 5")


@dataclass
class DownloadConfig:
    """Download configuration."""

    audio_quality: str = "HI_RES"
    download_path: Optional[Path] = None
    max_retries: int = 3
    retry_delay: int = 60
    delay_between_downloads: int = 5
    extract_flac: bool = False
    skip_existing: bool = True

    def __post_init__(self):
        """Validate configuration and set defaults."""
        if self.download_path is None:
            self.download_path = get_default_download_dir()
        elif isinstance(self.download_path, str):
            self.download_path = Path(self.download_path).expanduser()

        # Validate audio quality
        valid_qualities = ["LOW", "HIGH", "LOSSLESS", "HI_RES"]
        if self.audio_quality not in valid_qualities:
            raise ValueError(f"audio_quality must be one of {valid_qualities}")

        # Validate retry settings
        if not (0 <= self.max_retries <= 10):
            raise ValueError("max_retries must be between 0 and 10")

        if self.retry_delay < 10:
            raise ValueError("retry_delay must be >= 10 seconds")

        if self.delay_between_downloads < 1:
            raise ValueError("delay_between_downloads must be >= 1 second")


@dataclass
class NotificationConfig:
    """Notification configuration."""

    enabled: bool = True
    desktop: bool = True
    on_new_tracks: bool = True
    on_download_complete: bool = True
    on_error: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration."""

    path: Optional[Path] = None
    level: str = "INFO"
    max_size_mb: int = 10
    backup_count: int = 5

    def __post_init__(self):
        """Validate configuration and set defaults."""
        if self.path is None:
            self.path = get_config_dir() / 'service.log'
        elif isinstance(self.path, str):
            self.path = Path(self.path).expanduser()

        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ValueError(f"level must be one of {valid_levels}")


@dataclass
class Settings:
    """Main settings container."""

    tidal: TidalConfig = field(default_factory=TidalConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_file(cls, config_path: Path) -> 'Settings':
        """Load settings from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Settings instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        # Create config objects with validation
        return cls(
            tidal=TidalConfig(**(data.get('tidal', {}))),
            database=DatabaseConfig(**(data.get('database', {}))),
            scheduler=SchedulerConfig(**(data.get('scheduler', {}))),
            download=DownloadConfig(**(data.get('download', {}))),
            notifications=NotificationConfig(**(data.get('notifications', {}))),
            logging=LoggingConfig(**(data.get('logging', {}))),
        )

    @classmethod
    def from_file_or_default(cls, config_path: Optional[Path] = None) -> 'Settings':
        """Load settings from file or return defaults.

        Args:
            config_path: Path to configuration file (optional)

        Returns:
            Settings instance
        """
        if config_path is None:
            config_path = get_config_dir() / 'config.yaml'

        if config_path.exists():
            try:
                return cls.from_file(config_path)
            except Exception as e:
                logging.warning(f"Failed to load config from {config_path}: {e}")
                logging.warning("Using default configuration")
                return cls()
        else:
            logging.info(f"Config file not found at {config_path}, using defaults")
            return cls()

    def save(self, config_path: Optional[Path] = None) -> None:
        """Save settings to YAML file.

        Args:
            config_path: Path to save configuration (default: config.yaml in config dir)
        """
        if config_path is None:
            config_path = get_config_dir() / 'config.yaml'

        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict for YAML serialization
        data = {
            'tidal': {
                'token_path': str(self.tidal.token_path) if self.tidal.token_path else None
            },
            'database': {
                'path': str(self.database.path) if self.database.path else None
            },
            'scheduler': {
                'check_interval_minutes': self.scheduler.check_interval_minutes,
                'use_cron_schedule': self.scheduler.use_cron_schedule,
                'cron_schedule': self.scheduler.cron_schedule
            },
            'download': {
                'audio_quality': self.download.audio_quality,
                'download_path': str(self.download.download_path) if self.download.download_path else None,
                'max_retries': self.download.max_retries,
                'retry_delay': self.download.retry_delay,
                'delay_between_downloads': self.download.delay_between_downloads,
                'extract_flac': self.download.extract_flac,
                'skip_existing': self.download.skip_existing
            },
            'notifications': {
                'enabled': self.notifications.enabled,
                'desktop': self.notifications.desktop,
                'on_new_tracks': self.notifications.on_new_tracks,
                'on_download_complete': self.notifications.on_download_complete,
                'on_error': self.notifications.on_error
            },
            'logging': {
                'path': str(self.logging.path) if self.logging.path else None,
                'level': self.logging.level,
                'max_size_mb': self.logging.max_size_mb,
                'backup_count': self.logging.backup_count
            }
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
