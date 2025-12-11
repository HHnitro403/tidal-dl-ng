# Windows Setup Guide - TIDAL Playlist Monitor

This guide covers Windows-specific installation and setup for the TIDAL Playlist Monitor.

## Prerequisites

1. **Python 3.12 or 3.13**
   ```cmd
   # Install via winget (recommended)
   winget install Python.Python.3.12

   # Or download from python.org
   # https://www.python.org/downloads/
   ```

2. **tidal-dl-ng**
   ```cmd
   pip install tidal-dl-ng
   ```

## Installation Steps

### 1. Set Up Virtual Environment

```cmd
# Navigate to project directory
cd C:\path\to\tidal-playlist-monitor

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Authenticate with TIDAL

```cmd
# Authenticate tidal-dl-ng
tidal-dl-ng login

# Follow on-screen instructions to log in via browser
```

### 3. Initialize Configuration

```cmd
# Create default config file
python -m tidal-playlist-monitor.cli init-config

# Config will be created at: %APPDATA%\tidal-playlist-monitor\config.yaml
```

### 4. Important Windows Configuration

Edit `%APPDATA%\tidal-playlist-monitor\config.yaml` and ensure:

```yaml
download:
  extract_flac: false  # CRITICAL: Prevents terminal flash on Windows
```

## Windows-Specific Limitations & Workarounds

### Issue #1: Terminal Window Flash During Downloads

**Problem:** When tidal-dl-ng uses FFmpeg for FLAC extraction, a terminal window briefly appears.

**Solution:** Disable FLAC extraction in config:
```yaml
download:
  extract_flac: false
```

This is automatically configured by the downloader, but you can verify in your config file.

### Issue #2: Running Silently in Background

**Problem:** Running Python scripts shows a console window.

**Solution:** Use `pythonw.exe` instead of `python.exe`:
```cmd
# Instead of:
python -m tidal-playlist-monitor.service

# Use:
pythonw -m tidal-playlist-monitor.service
```

The `w` suffix runs Python without a console window.

### Issue #3: No Daemon Mode

**Problem:** Windows doesn't support Unix-style daemon processes.

**Solutions:** See "Auto-Start on Windows" section below.

## Running the Service

### Foreground (for testing)

```cmd
# Activate virtual environment
venv\Scripts\activate

# Start service
python -m tidal-playlist-monitor.cli start

# Press Ctrl+C to stop
```

### Background (silent)

```cmd
# Activate virtual environment
venv\Scripts\activate

# Start in background
pythonw -m tidal-playlist-monitor.service
```

## Auto-Start on Windows

### Option 1: Task Scheduler (Recommended)

**Advantages:**
- Runs even when not logged in
- Automatic restart on failure
- Full control over scheduling

**Setup Steps:**

1. **Open Task Scheduler**
   - Press `Win+R`, type `taskschd.msc`, press Enter

2. **Create Basic Task**
   - Click "Create Task" (not "Create Basic Task")
   - Name: `TIDAL Playlist Monitor`

3. **General Tab**
   - ✅ Run whether user is logged on or not
   - ✅ Run with highest privileges
   - Configure for: Windows 10

4. **Triggers Tab**
   - New → Begin the task: "At startup"
   - Delay task for: 30 seconds (allows network to initialize)

5. **Actions Tab**
   - New → Start a program
   - **Program/script:** `C:\path\to\venv\Scripts\pythonw.exe`
   - **Add arguments:** `-m tidal-playlist-monitor.service`
   - **Start in:** `C:\path\to\tidal-playlist-monitor`

6. **Conditions Tab**
   - ✅ Start only if the following network connection is available: Any connection
   - ⬜ Start the task only if the computer is on AC power (uncheck if laptop)

7. **Settings Tab**
   - ✅ Allow task to be run on demand
   - ✅ Run task as soon as possible after a scheduled start is missed
   - If the task fails, restart every: 1 minute
   - Attempt to restart up to: 3 times

8. **Save Task**
   - Enter your Windows password when prompted

**Verify:**
```cmd
# Run task manually
schtasks /run /tn "TIDAL Playlist Monitor"

# Check status
schtasks /query /tn "TIDAL Playlist Monitor"
```

**PowerShell Script (Alternative):**

```powershell
# Run as Administrator
$action = New-ScheduledTaskAction `
    -Execute "C:\path\to\venv\Scripts\pythonw.exe" `
    -Argument "-m tidal-playlist-monitor.service" `
    -WorkingDirectory "C:\path\to\tidal-playlist-monitor"

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERNAME" `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName "TIDAL Playlist Monitor" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Monitors TIDAL playlists and auto-downloads new tracks"
```

### Option 2: Startup Folder (Simpler, but requires login)

**Advantages:**
- Very simple setup
- No elevated privileges needed

**Disadvantages:**
- Only runs when you log in
- Visible in Task Manager

**Setup Steps:**

1. **Create Startup Script**

Create `tidal_monitor_start.pyw`:
```python
import subprocess
import sys
from pathlib import Path

# Get script directory
script_dir = Path(__file__).parent

# Path to virtual environment Python
python_exe = script_dir / 'venv' / 'Scripts' / 'pythonw.exe'

# Start service silently
subprocess.Popen(
    [str(python_exe), '-m', 'tidal-playlist-monitor.service'],
    cwd=script_dir,
    creationflags=subprocess.CREATE_NO_WINDOW
)
```

2. **Add to Startup Folder**
   - Press `Win+R`, type `shell:startup`, press Enter
   - Copy `tidal_monitor_start.pyw` to this folder
   - OR create a shortcut to the file

3. **Test**
   - Double-click the `.pyw` file - nothing should appear
   - Check Task Manager → Details → look for `pythonw.exe`
   - Check logs: `%APPDATA%\tidal-playlist-monitor\service.log`

### Option 3: Windows Service (Advanced)

**Advantages:**
- True Windows service
- Full integration with Service Control Manager
- Can run before user login

**Disadvantages:**
- More complex setup
- Requires additional package (`pywin32`)

**Setup:**

1. Install pywin32:
```cmd
pip install pywin32
```

2. Create service wrapper (example structure):

```python
# service_wrapper.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys

class TidalMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TidalPlaylistMonitor"
    _svc_display_name_ = "TIDAL Playlist Monitor"
    _svc_description_ = "Monitors TIDAL playlists for changes"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()

    def main(self):
        # Import and run service
        from tidal_playlist_monitor.service import TidalPlaylistService
        service = TidalPlaylistService()
        service.start()

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TidalMonitorService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(TidalMonitorService)
```

3. Install and manage service:
```cmd
# Install
python service_wrapper.py install

# Start
python service_wrapper.py start

# Stop
python service_wrapper.py stop

# Remove
python service_wrapper.py remove
```

## Checking Service Status

### Task Manager
1. Press `Ctrl+Shift+Esc`
2. Go to "Details" tab
3. Look for `pythonw.exe`

### Logs
```cmd
# View log file
type %APPDATA%\tidal-playlist-monitor\service.log

# Tail log file (PowerShell)
Get-Content %APPDATA%\tidal-playlist-monitor\service.log -Wait -Tail 50
```

### CLI Status Command
```cmd
python -m tidal-playlist-monitor.cli status
```

## Stopping the Service

### If running in foreground
Press `Ctrl+C`

### If started via Task Scheduler
```cmd
schtasks /end /tn "TIDAL Playlist Monitor"
```

### If running in background (pythonw)
1. Open Task Manager (`Ctrl+Shift+Esc`)
2. Find `pythonw.exe` running the service
3. Right-click → End Task

## Troubleshooting

### Service doesn't start
- Check Python path in Task Scheduler is correct
- Verify virtual environment is activated
- Check logs in `%APPDATA%\tidal-playlist-monitor\service.log`

### Terminal window still appears
- Ensure `extract_flac: false` in config
- Verify using `pythonw.exe` not `python.exe`
- Check tidal-dl-ng config: `tidal-dl-ng cfg extract_flac false`

### Notifications don't appear
- Install winotify: `pip install winotify`
- Check Windows notification settings:
  - Settings → System → Notifications
  - Ensure notifications are enabled

### Can't find config file
```cmd
# Print config directory
echo %APPDATA%\tidal-playlist-monitor

# Open directory
explorer %APPDATA%\tidal-playlist-monitor
```

### Service crashes on startup
- Check authentication: `tidal-dl-ng login`
- Verify config file is valid YAML
- Check logs for error messages
- Run in foreground to see errors: `python -m tidal-playlist-monitor.cli start`

## Performance Tips

### Reduce CPU/Network usage
Edit config:
```yaml
scheduler:
  check_interval_minutes: 60  # Check less frequently

download:
  delay_between_downloads: 10  # Longer delays between downloads
```

### Reduce disk space
- Set download path to larger drive
- Use lower quality: `audio_quality: HIGH`
- Enable skip_existing: `skip_existing: true`

## Uninstallation

1. **Stop service**
   ```cmd
   # Task Scheduler
   schtasks /end /tn "TIDAL Playlist Monitor"
   schtasks /delete /tn "TIDAL Playlist Monitor"

   # Or kill process
   taskkill /IM pythonw.exe /F
   ```

2. **Remove auto-start**
   - Delete from Startup folder
   - Or remove scheduled task

3. **Delete files**
   ```cmd
   # Remove application data
   rmdir /s /q %APPDATA%\tidal-playlist-monitor

   # Remove project directory
   rmdir /s /q C:\path\to\tidal-playlist-monitor
   ```

## Support

For issues specific to tidal-dl-ng integration, see the [main repository](https://github.com/exislow/tidal-dl-ng).
