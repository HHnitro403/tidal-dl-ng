"""Platform-specific utilities for cross-platform compatibility."""

import os
import sys
from pathlib import Path


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == 'win32' or os.name == 'nt'


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == 'darwin'


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith('linux')


def get_config_dir() -> Path:
    """Get the configuration directory based on the platform.

    Returns:
        Path: Configuration directory path
            - Windows: %APPDATA%/tidal-playlist-monitor
            - macOS: ~/Library/Application Support/tidal-playlist-monitor
            - Linux: ~/.config/tidal-playlist-monitor
    """
    if is_windows():
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif is_macos():
        base = Path.home() / 'Library' / 'Application Support'
    else:  # Linux and others
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))

    config_dir = base / 'tidal-playlist-monitor'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_default_download_dir() -> Path:
    """Get the default download directory based on the platform.

    Returns:
        Path: Default download directory
            - Windows: ~/Music/TIDAL
            - macOS: ~/Music/TIDAL
            - Linux: ~/Music/TIDAL (falls back to ~/Downloads/TIDAL if ~/Music doesn't exist)
    """
    music_dir = Path.home() / 'Music'

    if music_dir.exists():
        download_dir = music_dir / 'TIDAL'
    else:
        download_dir = Path.home() / 'Downloads' / 'TIDAL'

    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir


def get_data_dir() -> Path:
    """Get the data directory for database and logs.

    For simplicity, uses the same directory as config.

    Returns:
        Path: Data directory path
    """
    return get_config_dir()
