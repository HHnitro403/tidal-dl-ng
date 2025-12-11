# TIDAL Playlist Auto-Sync Monitor

A background service that monitors TIDAL playlists for changes and automatically downloads new tracks using [tidal-dl-ng](https://github.com/exislow/tidal-dl-ng).

## Features

- ✅ **Automatic Monitoring** - Periodically checks TIDAL playlists for new tracks
- ✅ **Smart Downloads** - Only downloads newly added tracks
- ✅ **Cross-Platform** - Works on Windows, Linux, and macOS
- ✅ **Configurable** - Extensive YAML configuration
- ✅ **Notifications** - Desktop notifications for new tracks and downloads
- ✅ **Persistent State** - SQLite database tracks playlist history
- ✅ **Windows Compatible** - No terminal flash, runs silently in background
- ✅ **CLI Management** - Easy command-line interface for playlist management

## Requirements

- Python 3.12 or 3.13
- TIDAL HiFi or HiFi Plus subscription
- [tidal-dl-ng](https://github.com/exislow/tidal-dl-ng) installed and authenticated

## Installation

### 1. Install Python Dependencies

```bash
# Clone or download this directory
cd tidal-playlist-monitor

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install and Authenticate tidal-dl-ng

```bash
# Install tidal-dl-ng
pip install tidal-dl-ng

# Authenticate with TIDAL
tidal-dl-ng login
# Follow the on-screen instructions to log in via browser
```

### 3. Initialize Configuration

```bash
# Create default config file
python -m tidal-playlist-monitor.cli init-config

# Edit configuration (optional)
# Windows: notepad %APPDATA%\tidal-playlist-monitor\config.yaml
# Linux/macOS: nano ~/.config/tidal-playlist-monitor/config.yaml
```

## Quick Start

### Add a Playlist to Monitor

```bash
python -m tidal-playlist-monitor.cli add-playlist "https://tidal.com/browse/playlist/YOUR-PLAYLIST-ID"
```

### List Monitored Playlists

```bash
python -m tidal-playlist-monitor.cli list-playlists
```

### Check for New Tracks Immediately

```bash
python -m tidal-playlist-monitor.cli check-now
```

### Start the Background Service

```bash
python -m tidal-playlist-monitor.cli start
```

The service will:
1. Check all monitored playlists every 30 minutes (configurable)
2. Detect newly added tracks
3. Automatically download them using tidal-dl-ng
4. Send desktop notifications

Press `Ctrl+C` to stop the service.

## Configuration

Configuration file location:
- **Windows:** `%APPDATA%\tidal-playlist-monitor\config.yaml`
- **Linux:** `~/.config/tidal-playlist-monitor/config.yaml`
- **macOS:** `~/Library/Application Support/tidal-playlist-monitor/config.yaml`

### Key Configuration Options

```yaml
scheduler:
  check_interval_minutes: 30  # How often to check for changes

download:
  audio_quality: HI_RES       # LOW, HIGH, LOSSLESS, HI_RES
  download_path: null         # null = default (~/Music/TIDAL)
  extract_flac: false         # Set to false on Windows to avoid terminal flash
  skip_existing: true         # Don't re-download existing tracks

notifications:
  enabled: true               # Enable/disable all notifications
  on_new_tracks: true         # Notify when new tracks found
  on_download_complete: true  # Notify when downloads complete

logging:
  level: INFO                 # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

See [config.yaml.example](config.yaml.example) for all options.

## Running as a Background Service

### Windows - Task Scheduler (Recommended)

1. Open Task Scheduler
2. Create new task:
   - **Name:** TIDAL Playlist Monitor
   - **Trigger:** At startup
   - **Action:** Start a program
     - **Program:** `pythonw.exe` (note the 'w' - runs without console)
     - **Arguments:** `-m tidal-playlist-monitor.service`
     - **Start in:** `C:\path\to\tidal-playlist-monitor`
   - **Settings:**
     - ✅ Allow task to run on demand
     - ✅ Run whether user is logged in or not

### Windows - Startup Folder (Simpler)

1. Create a `.pyw` file (Python without console):

```python
# tidal_monitor_start.pyw
import subprocess
import sys
from pathlib import Path

script_dir = Path(__file__).parent
subprocess.Popen([
    sys.executable,
    '-m',
    'tidal-playlist-monitor.service'
], cwd=script_dir)
```

2. Place shortcut in startup folder:
   - Press `Win+R`, type `shell:startup`, press Enter
   - Create shortcut to `tidal_monitor_start.pyw`

### Linux - systemd

```bash
# Create service file
sudo nano /etc/systemd/system/tidal-monitor.service

# Add:
[Unit]
Description=TIDAL Playlist Monitor
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/tidal-playlist-monitor
ExecStart=/home/youruser/tidal-playlist-monitor/venv/bin/python -m tidal-playlist-monitor.service
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable tidal-monitor
sudo systemctl start tidal-monitor
sudo systemctl status tidal-monitor
```

### macOS - launchd

Create `~/Library/LaunchAgents/com.user.tidal-monitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.tidal-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>-m</string>
        <string>tidal-playlist-monitor.service</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/tidal-playlist-monitor</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Then:
```bash
launchctl load ~/Library/LaunchAgents/com.user.tidal-monitor.plist
```

## CLI Commands

### Service Management

```bash
# Start service
python -m tidal-playlist-monitor.cli start

# Check service status
python -m tidal-playlist-monitor.cli status
```

### Playlist Management

```bash
# Add playlist
python -m tidal-playlist-monitor.cli add-playlist <URL>

# List playlists
python -m tidal-playlist-monitor.cli list-playlists

# Remove playlist
python -m tidal-playlist-monitor.cli remove-playlist <ID>
```

### Manual Operations

```bash
# Trigger immediate check
python -m tidal-playlist-monitor.cli check-now

# Initialize config file
python -m tidal-playlist-monitor.cli init-config
```

## Troubleshooting

### "tidal-dl-ng not authenticated"

Run `tidal-dl-ng login` to authenticate.

### Terminal window flashes on Windows

Set `extract_flac: false` in config.yaml.

### No notifications appearing

Check notification permissions in system settings. Install `winotify` on Windows:
```bash
pip install winotify
```

### Service exits immediately

- On Windows: Ensure using `pythonw.exe` not `python.exe`
- Check logs: `%APPDATA%\tidal-playlist-monitor\service.log`

### Playlist not detected

- Verify playlist ID/URL is correct
- Ensure playlist is public or you are the owner
- Check TIDAL authentication is valid

## File Locations

### Windows
- **Config:** `%APPDATA%\tidal-playlist-monitor\config.yaml`
- **Database:** `%APPDATA%\tidal-playlist-monitor\monitor.db`
- **Logs:** `%APPDATA%\tidal-playlist-monitor\service.log`
- **TIDAL Token:** `%APPDATA%\tidal-playlist-monitor\tidal_token.json`

### Linux
- **Config:** `~/.config/tidal-playlist-monitor/config.yaml`
- **Database:** `~/.config/tidal-playlist-monitor/monitor.db`
- **Logs:** `~/.config/tidal-playlist-monitor/service.log`
- **TIDAL Token:** `~/.config/tidal-playlist-monitor/tidal_token.json`

### macOS
- **Config:** `~/Library/Application Support/tidal-playlist-monitor/config.yaml`
- **Database:** `~/Library/Application Support/tidal-playlist-monitor/monitor.db`
- **Logs:** `~/Library/Application Support/tidal-playlist-monitor/service.log`
- **TIDAL Token:** `~/Library/Application Support/tidal-playlist-monitor/tidal_token.json`

## How It Works

1. **Monitoring:** Service checks TIDAL playlists at configured intervals
2. **Detection:** Compares current playlist tracks with stored snapshot in database
3. **Download:** Newly detected tracks are queued and downloaded via tidal-dl-ng
4. **Notification:** Desktop notifications inform you of new tracks and downloads
5. **State Persistence:** All data stored in SQLite database, survives restarts

## Architecture

```
tidal-playlist-monitor/
├── config/
│   ├── settings.py       # Configuration management
│   └── database.py       # SQLite database handler
├── core/
│   ├── monitor.py        # Playlist change detection
│   ├── downloader.py     # Download manager (Windows-compatible)
│   ├── scheduler.py      # APScheduler integration
│   └── notifier.py       # Cross-platform notifications
├── models/
│   ├── playlist.py       # Playlist data model
│   ├── track.py          # Track data model
│   └── download.py       # Download status model
├── utils/
│   ├── platform.py       # Platform detection & paths
│   └── logger.py         # Logging configuration
├── cli.py                # Command-line interface
├── service.py            # Main background service
└── requirements.txt      # Python dependencies
```

## Contributing

This project is part of the tidal-dl-ng ecosystem. For issues or feature requests, please visit the [tidal-dl-ng repository](https://github.com/exislow/tidal-dl-ng).

## License

This project follows the same license as tidal-dl-ng.

## Credits

- Built on top of [tidal-dl-ng](https://github.com/exislow/tidal-dl-ng)
- Uses [tidalapi](https://github.com/tamland/python-tidal) for TIDAL API access
