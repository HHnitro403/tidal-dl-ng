# Quick Start Guide

## ✅ Fixed! Now You Can Use It

The package has been reorganized and installed. Here's how to use it:

---

## 🚀 Quick Setup (3 Steps)

### 1. Authenticate with TIDAL

```bash
tidal-dl-ng login
```

Open the URL in your browser and log in.

### 2. Initialize Configuration

```bash
tidal-playlist-monitor init-config
```

This creates: `%APPDATA%\tidal-playlist-monitor\config.yaml`

### 3. Add a Playlist

```bash
tidal-playlist-monitor add-playlist "https://tidal.com/browse/playlist/YOUR-PLAYLIST-ID"
```

---

## ▶️ Run the Service

### Test Mode (Foreground)

```bash
tidal-playlist-monitor start
```

Press Ctrl+C to stop.

### Background Mode (Silent)

```bash
pythonw -m tidal_playlist_monitor.service
```

No console window appears!

---

## 📊 Useful Commands

```bash
# Check status
tidal-playlist-monitor status

# List playlists
tidal-playlist-monitor list-playlists

# Check for new tracks now
tidal-playlist-monitor check-now

# Remove a playlist
tidal-playlist-monitor remove-playlist PLAYLIST_ID
```

---

## 🪟 Windows: Auto-Start on Boot

### Quick Method

1. Create `start_monitor.pyw`:

```python
import subprocess
import sys
from pathlib import Path

subprocess.Popen(
    ['tidal-playlist-monitor', 'start'],
    creationflags=subprocess.CREATE_NO_WINDOW
)
```

2. Press `Win+R`, type `shell:startup`, press Enter
3. Copy `start_monitor.pyw` to that folder

Done! It auto-starts when you log in.

---

## ⚙️ Configuration

Edit: `%APPDATA%\tidal-playlist-monitor\config.yaml`

```yaml
scheduler:
  check_interval_minutes: 30  # How often to check

download:
  audio_quality: HI_RES       # LOW, HIGH, LOSSLESS, HI_RES
  extract_flac: false         # Keep false on Windows!

notifications:
  enabled: true               # Desktop notifications
```

---

## 📁 Downloads Location

Default: `C:\Users\YourName\Music\TIDAL\`

Change in config:
```yaml
download:
  download_path: "D:\\My Music\\TIDAL"
```

---

## 🔍 View Logs

```bash
type %APPDATA%\tidal-playlist-monitor\service.log
```

---

## 🆘 Troubleshooting

### Service won't start
- Check: `tidal-dl-ng login` (authenticate first)
- Check logs (see above)

### No notifications
```bash
pip install winotify
```

### Terminal flashes
Config must have:
```yaml
download:
  extract_flac: false
```

---

## 🎯 Example Workflow

```bash
# 1. Authenticate
tidal-dl-ng login

# 2. Setup
tidal-playlist-monitor init-config

# 3. Add playlists
tidal-playlist-monitor add-playlist "https://tidal.com/browse/playlist/123..."
tidal-playlist-monitor add-playlist "https://tidal.com/browse/playlist/456..."

# 4. Test
tidal-playlist-monitor check-now

# 5. Run in background
pythonw -m tidal_playlist_monitor.service
```

**Done!** New tracks will auto-download as they appear in your playlists.

---

## 📚 More Help

- **Full Guide:** See `README.md`
- **Windows Details:** See `WINDOWS_GUIDE.md`
- **All Config Options:** See `config.yaml.example`
