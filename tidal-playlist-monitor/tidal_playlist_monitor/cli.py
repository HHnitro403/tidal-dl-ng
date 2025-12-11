"""Command-line interface for TIDAL Playlist Monitor."""

import sys
from pathlib import Path
from typing import Optional

import tidalapi
import typer
from rich.console import Console
from rich.table import Table

from .config.database import DatabaseHandler
from .config.settings import Settings
from .models.playlist import Playlist as PlaylistModel
from .utils.logger import setup_logger
from .utils.platform import get_config_dir

app = typer.Typer(help="TIDAL Playlist Auto-Sync Monitor")
console = Console()


def get_settings(config_path: Optional[Path] = None) -> Settings:
    """Load settings from file or defaults."""
    return Settings.from_file_or_default(config_path)


def get_database(settings: Settings) -> DatabaseHandler:
    """Get database handler."""
    return DatabaseHandler(settings.database.path)


def get_tidal_session(settings: Settings) -> tidalapi.Session:
    """Get authenticated TIDAL session."""
    session = tidalapi.Session()

    # Try to load existing token
    token_path = settings.tidal.token_path

    if token_path and token_path.exists():
        try:
            # Try to load from JSON file
            import json
            with open(token_path, 'r') as f:
                token_data = json.load(f)

            # Load the session with token data
            session.load_oauth_session(
                token_data.get('token_type'),
                token_data.get('access_token'),
                token_data.get('refresh_token'),
                token_data.get('expiry_time')
            )

            if session.check_login():
                return session
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load token: {e}[/yellow]")

    # Need to authenticate
    console.print("[yellow]TIDAL authentication required[/yellow]")
    console.print("\nPlease visit the URL shown below and log in with your TIDAL account:")

    session.login_oauth_simple()

    # Save token manually
    if token_path:
        token_path.parent.mkdir(parents=True, exist_ok=True)

        import json
        token_data = {
            'token_type': session.token_type,
            'access_token': session.access_token,
            'refresh_token': session.refresh_token,
            'expiry_time': session.expiry_time.timestamp() if hasattr(session.expiry_time, 'timestamp') else session.expiry_time
        }

        with open(token_path, 'w') as f:
            json.dump(token_data, f, indent=2)

        console.print(f"\n[green]Token saved to {token_path}[/green]")

    return session


def extract_playlist_id(url_or_id: str) -> str:
    """Extract playlist ID from URL or return as-is if already an ID.

    Args:
        url_or_id: TIDAL playlist URL or ID

    Returns:
        Playlist ID

    Raises:
        ValueError: If URL format is invalid
    """
    if url_or_id.startswith('http'):
        # Extract ID from URL
        # Format: https://tidal.com/browse/playlist/<UUID>
        parts = url_or_id.rstrip('/').split('/')
        if 'playlist' in parts:
            idx = parts.index('playlist')
            if idx + 1 < len(parts):
                return parts[idx + 1]
        raise ValueError(f"Invalid playlist URL format: {url_or_id}")
    else:
        # Assume it's already an ID
        return url_or_id


@app.command()
def start(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    daemon: bool = typer.Option(
        False,
        "--daemon",
        "-d",
        help="Run as daemon (Linux/macOS only)"
    )
):
    """Start the monitoring service."""
    if daemon and sys.platform == 'win32':
        console.print("[red]Error: Daemon mode not supported on Windows[/red]")
        console.print("Use Task Scheduler or Startup folder instead")
        raise typer.Exit(1)

    console.print("[cyan]Starting TIDAL Playlist Monitor service...[/cyan]")

    # Import here to avoid circular dependency
    from .service import TidalPlaylistService

    try:
        service = TidalPlaylistService(config_path=config)
        service.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Service stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Service error: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="add-playlist")
def add_playlist(
    url: str = typer.Argument(..., help="TIDAL playlist URL or ID"),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    )
):
    """Add a playlist to monitoring."""
    settings = get_settings(config)
    db = get_database(settings)

    try:
        # Extract playlist ID
        playlist_id = extract_playlist_id(url)

        # Check if already exists
        existing = db.get_playlist(playlist_id)
        if existing:
            console.print(f"[yellow]Playlist '{existing.name}' is already being monitored[/yellow]")

            enable = typer.confirm("Enable it?", default=True)
            if enable:
                db.enable_playlist(playlist_id, True)
                console.print("[green]Playlist enabled[/green]")
            return

        # Get TIDAL session
        console.print("Connecting to TIDAL...")
        session = get_tidal_session(settings)

        # Fetch playlist metadata
        console.print(f"Fetching playlist {playlist_id}...")
        tidal_playlist = session.playlist(playlist_id)

        if not tidal_playlist:
            console.print(f"[red]Error: Playlist {playlist_id} not found[/red]")
            raise typer.Exit(1)

        # Get track count
        num_tracks = tidal_playlist.num_tracks or 0

        # Create playlist model
        playlist = PlaylistModel(
            playlist_id=playlist_id,
            name=tidal_playlist.name,
            description=tidal_playlist.description,
            owner=tidal_playlist.creator.name if tidal_playlist.creator else None,
            track_count=num_tracks,
            enabled=True
        )

        # Add to database
        db.add_playlist(playlist)

        console.print(f"[green]Successfully added playlist: {playlist.name}[/green]")
        console.print(f"Tracks: {num_tracks}")
        console.print(f"Owner: {playlist.owner or 'Unknown'}")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed to add playlist: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="remove-playlist")
def remove_playlist(
    playlist_id: str = typer.Argument(..., help="Playlist ID to remove"),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    )
):
    """Remove a playlist from monitoring."""
    settings = get_settings(config)
    db = get_database(settings)

    try:
        # Check if exists
        playlist = db.get_playlist(playlist_id)
        if not playlist:
            console.print(f"[red]Playlist {playlist_id} not found[/red]")
            raise typer.Exit(1)

        # Confirm removal
        console.print(f"Playlist: {playlist.name}")
        console.print(f"Tracks: {playlist.track_count}")

        confirm = typer.confirm("Remove this playlist from monitoring?", default=False)

        if confirm:
            db.remove_playlist(playlist_id)
            console.print("[green]Playlist removed[/green]")
        else:
            console.print("[yellow]Cancelled[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="list-playlists")
def list_playlists(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show disabled playlists too"
    )
):
    """List all monitored playlists."""
    settings = get_settings(config)
    db = get_database(settings)

    try:
        playlists = db.get_monitored_playlists(enabled_only=not all)

        if not playlists:
            console.print("[yellow]No playlists being monitored[/yellow]")
            console.print("\nUse 'add-playlist' command to add playlists")
            return

        # Create table
        table = Table(title="Monitored Playlists")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Tracks", justify="right")
        table.add_column("Last Checked")
        table.add_column("Status")

        for playlist in playlists:
            last_checked = (
                playlist.last_checked.strftime("%Y-%m-%d %H:%M")
                if playlist.last_checked
                else "Never"
            )

            status = "[green]Enabled[/green]" if playlist.enabled else "[red]Disabled[/red]"

            table.add_row(
                playlist.playlist_id[:8] + "...",
                playlist.name,
                str(playlist.track_count),
                last_checked,
                status
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="check-now")
def check_now(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    )
):
    """Trigger an immediate playlist check."""
    console.print("[cyan]Checking playlists for changes...[/cyan]")

    # Import here to avoid circular dependency
    from .core.downloader import TidalDownloader
    from .core.monitor import PlaylistMonitor

    settings = get_settings(config)
    db = get_database(settings)

    try:
        # Get TIDAL session
        session = get_tidal_session(settings)

        # Setup logger
        logger = setup_logger(
            log_file=None,  # Console only for manual check
            level="INFO",
            console=True
        )

        # Create monitor
        monitor = PlaylistMonitor(session, db, logger)

        # Create downloader
        downloader = TidalDownloader(
            db=db,
            logger=logger,
            quality=settings.download.audio_quality,
            download_path=settings.download.download_path,
            skip_existing=settings.download.skip_existing,
            max_retries=settings.download.max_retries,
            retry_delay=settings.download.retry_delay,
            delay_between_downloads=settings.download.delay_between_downloads
        )

        # Configure downloader
        downloader.configure_quality()

        # Check all playlists
        results = monitor.check_all_playlists()

        total_new = sum(len(tracks) for tracks in results.values())

        if total_new == 0:
            console.print("[green]No new tracks found[/green]")
            return

        console.print(f"[green]Found {total_new} new track(s)[/green]")

        # Download new tracks
        all_new_tracks = [track for tracks in results.values() for track in tracks]

        if all_new_tracks:
            console.print(f"\nDownloading {len(all_new_tracks)} track(s)...")
            download_results = downloader.download_batch(all_new_tracks)

            console.print(
                f"[green]Download complete: {download_results['success']} successful, "
                f"{download_results['failed']} failed[/green]"
            )

    except Exception as e:
        console.print(f"[red]Check failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file"
    )
):
    """Show service status and statistics."""
    settings = get_settings(config)
    db = get_database(settings)

    try:
        # Get statistics
        playlists = db.get_monitored_playlists(enabled_only=False)
        download_stats = db.get_download_stats()

        # Display stats
        console.print("[cyan]TIDAL Playlist Monitor Status[/cyan]\n")

        console.print(f"Config directory: {get_config_dir()}")
        console.print(f"Database: {settings.database.path}")
        console.print(f"Log file: {settings.logging.path}\n")

        console.print(f"[bold]Playlists:[/bold]")
        enabled_count = sum(1 for p in playlists if p.enabled)
        console.print(f"  Total: {len(playlists)}")
        console.print(f"  Enabled: {enabled_count}")
        console.print(f"  Disabled: {len(playlists) - enabled_count}\n")

        console.print(f"[bold]Downloads:[/bold]")
        console.print(f"  Completed: {download_stats.get('completed', 0)}")
        console.print(f"  Failed: {download_stats.get('failed', 0)}")
        console.print(f"  Pending: {download_stats.get('pending', 0)}")
        console.print(f"  Downloading: {download_stats.get('downloading', 0)}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init_config(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for config file"
    )
):
    """Initialize a configuration file with defaults."""
    if output is None:
        output = get_config_dir() / 'config.yaml'

    if output.exists():
        overwrite = typer.confirm(
            f"Config file already exists at {output}. Overwrite?",
            default=False
        )
        if not overwrite:
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Create default settings and save
    settings = Settings()
    settings.save(output)

    console.print(f"[green]Configuration file created: {output}[/green]")
    console.print("\nEdit this file to customize your settings")


if __name__ == "__main__":
    app()
