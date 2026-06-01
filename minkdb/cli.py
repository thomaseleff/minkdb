"""CLI for Mink-db."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from minkdb import __version__
from minkdb.catalog import (
    find_and_parse_itunes,
    get_catalog_output,
    get_unique_albums,
    load_existing_catalog,
    parse_tracks,
)
from minkdb.database import AlbumEntry, append_to_catalog
from minkdb.musicbrainz import search_release_group_match
from minkdb.publish import PublishError, publish_to_lidarr

console = Console(force_terminal=True)


def echo_splash(
    title: str | None = None,
    subtitle: str | None = None,
    note: str | None = None,
    hint: str | None = None,
) -> None:
    """Display splash screen with tool info."""
    title = title or f"Mink-db v{__version__}"
    subtitle = subtitle or "A metadata-link between iTunes & MusicBrainz"
    experimental = "experimental"
    hint = hint or "Hint: Use `--rematch` to retry matching unmatched albums."

    note = note or (
        "MusicBrainz limits API requests to 1/sec.\n"
        "Large iTunes libraries may take some time or be rate limited.\n"
        "Mink-db picks up where it left off, so you may need to run\n"
        "the tool multiple times to complete the initial metadata-linking."
    )

    splash = (
        f"[bold cyan]{title}[/bold cyan] [yellow]{experimental}[/yellow]\n"
        f"[cyan]{subtitle}[/cyan]\n\n"
        f"[cyan]{hint}[/cyan]"
    )
    console.print(Panel(splash, expand=False, border_style="cyan"), end="")
    console.print(f"\n[yellow]Note:[/yellow] {note}")
    console.print()


def echo_step(number: int, description: str) -> None:
    """Display a step header."""
    console.print(f"[bold green][{number}][/bold green] {description}")


def echo_success(message: str) -> None:
    """Display a success message."""
    console.print(f"  [green]+[/green] {message}")


def echo_table(entries: list) -> None:
    """Display data as a rich table."""
    if not entries:
        return

    table = Table(show_header=True, header_style="bold cyan", box=None)

    table.add_column("Status", justify="center", width=8)
    table.add_column("Artist", style="white")
    table.add_column("Album", style="white")
    table.add_column("MusicBrainz ID", style="dim")

    for e in entries[:50]:
        status = "[green]Y[/green]" if e.musicbrainz_id else "[red]N[/red]"
        mbid = e.musicbrainz_id or "-"
        table.add_row(status, e.artist, e.album, mbid)

    console.print(table)

    if len(entries) > 50:
        console.print(f"  ... and {len(entries) - 50} more albums")


def run_catalog(
    library_path: Path | None,
    itunes_filename: str,
    output_file: Path | None,
    limit: int | None,
    rematch: bool,
) -> None:
    """Run the cataloging workflow."""
    echo_splash()

    if library_path is None:
        library_path = Path.cwd()
    else:
        library_path = Path(library_path)

    if not library_path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {library_path}")
        sys.exit(1)

    try:
        # Step 1: Find iTunes XML
        echo_step(1, "Finding iTunes XML file...")
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Searching", total=None)
            xml_path = find_and_parse_itunes(library_path, itunes_filename)
        echo_success(f"Found: {xml_path.name}")

        # Step 2: Parse tracks
        echo_step(2, "Parsing iTunes library...")
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Parsing", total=None)
            tracks = parse_tracks(xml_path)
        echo_success(f"Parsed {len(tracks)} tracks")

        # Step 3: Extract unique albums
        echo_step(3, "Extracting unique albums...")
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Extracting", total=None)
            unique_albums = get_unique_albums(tracks)
        echo_success(f"Found {len(unique_albums)} unique albums")

        # Step 4: Load existing catalog
        echo_step(4, "Loading existing catalog...")
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Loading", total=None)
            catalog = load_existing_catalog(library_path)

        if rematch:
            unmatched = [e for e in catalog if not e.musicbrainz_id]
            echo_success(f"Found {len(unmatched)} unmatched albums to rematch")
        else:
            unmatched = []
            matched = sum(1 for e in catalog if e.musicbrainz_id)
            total = len(catalog)
            ratio = f"{matched}/{total}" if total else "0/0"
            echo_success(f"Loaded {total} cataloged albums ({ratio} matched)")

        # Step 5: Process albums
        echo_step(5, "Processing albums...")

        if rematch:
            albums_to_process = [(e.artist, e.album) for e in unmatched]
        else:
            catalog_dict = {(e.artist, e.album): e for e in catalog}
            albums_to_process = [
                (a, b) for (a, b) in unique_albums if (a, b) not in catalog_dict
            ]

        total_albums = len(albums_to_process)
        if limit:
            total_albums = min(total_albums, limit)

        entries = list(catalog)

        if total_albums == 0:
            echo_success("No albums to process")
        else:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                TextColumn("[dim]{task.fields[current]}[/dim]"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "Processing",
                    total=total_albums,
                    current="",
                )

                albums_limited = albums_to_process[:total_albums]

                for artist, album in albums_limited:
                    existing_entry = next(
                        (e for e in catalog if e.artist == artist and e.album == album),
                        None,
                    )

                    if rematch and existing_entry:
                        match = search_release_group_match(artist, album)
                        if match.release_group_id:
                            existing_entry.musicbrainz_id = match.release_group_id
                            existing_entry.matched_at = (
                                datetime.now().replace(tzinfo=timezone.utc).isoformat()
                            )
                            existing_entry.status = "matched"
                            existing_entry.artist_musicbrainz_id = (
                                match.artist_musicbrainz_id
                            )
                            append_to_catalog(existing_entry, library_path)
                        entry = existing_entry
                    else:
                        match = search_release_group_match(artist, album)
                        timestamp = (
                            datetime.now().replace(tzinfo=timezone.utc).isoformat()
                        )
                        entry = AlbumEntry(
                            artist=artist,
                            album=album,
                            musicbrainz_id=match.release_group_id,
                            matched_at=timestamp if match.release_group_id else None,
                            status="matched" if match.release_group_id else "unmatched",
                            artist_musicbrainz_id=match.artist_musicbrainz_id,
                        )
                        append_to_catalog(entry, library_path)
                        entries.append(entry)

                    is_matched = entry.musicbrainz_id is not None
                    status_text = "matched" if is_matched else "unmatched"
                    if is_matched:
                        status = f"[green]{status_text}[/green]"
                    else:
                        status = f"[red]{status_text}[/red]"
                    progress.update(
                        task,
                        current=f"{artist} - {album} [{status}]",
                    )
                    progress.advance(task)

        # Step 6: Generate output
        echo_step(6, "Generating output...")
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Generating", total=None)
            output = get_catalog_output(entries)
        echo_success(f"Generated output for {len(output)} unique matched artists")

        # Step 7: Display/Write output
        matched = sum(1 for e in entries if e.musicbrainz_id)
        unmatched = len(entries) - matched

        console.print()
        echo_table(entries)

        console.print()
        console.print(
            f"Total: {len(entries)} albums | "
            f"[green]{matched}[/green] matched | "
            f"[red]{unmatched}[/red] unmatched"
        )

        output_json = json.dumps(output, indent=2)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(output_json)
            console.print(f"\n[cyan]Output written to: {output_path}[/cyan]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@click.group(invoke_without_command=True)
@click.option(
    "--path",
    "-p",
    "library_path",
    default=None,
    help="Path to iTunes library (defaults to current directory)",
)
@click.option(
    "--itunes",
    "-i",
    "itunes_filename",
    default="iTunes Music Library.xml",
    help="iTunes XML filename to search for",
)
@click.option(
    "--output",
    "-o",
    "output_file",
    default=None,
    help="Output file path (defaults to stdout)",
)
@click.option(
    "--limit",
    "-l",
    "limit",
    default=None,
    type=int,
    help="Limit number of albums to process",
)
@click.option(
    "--rematch",
    is_flag=True,
    default=False,
    help="Retry matching for previously unmatched albums",
)
@click.version_option(version=__version__)
@click.pass_context
def main(
    ctx: click.Context,
    library_path: Path | None,
    itunes_filename: str,
    output_file: Path | None,
    limit: int | None,
    rematch: bool,
) -> None:
    """Mink-db - A metadata-link between iTunes and MusicBrainz."""
    if ctx.invoked_subcommand is not None:
        return
    run_catalog(
        library_path=library_path,
        itunes_filename=itunes_filename,
        output_file=output_file,
        limit=limit,
        rematch=rematch,
    )


@main.command("publish")
@click.option(
    "--path",
    "-p",
    "library_path",
    required=True,
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    help="Path to iTunes library containing .minkdb/album.json",
)
@click.option(
    "--url",
    "lidarr_url",
    default="http://localhost:8686",
    show_default=True,
    help="Lidarr server URL",
)
@click.option(
    "--monitor",
    "monitor_type",
    type=click.Choice(["all", "exact", "none"]),
    default="exact",
    show_default=True,
    help="Artist monitoring level: all (all albums), exact (only published), none",
)
@click.option(
    "--quality",
    "quality_profile",
    default=None,
    help="Quality profile name to use (default: first profile)",
)
def publish(
    library_path: Path,
    lidarr_url: str,
    monitor_type: str,
    quality_profile: str | None,
) -> None:
    """Publish curated exact albums from Mink-db to Lidarr."""
    echo_splash(
        title="Publish to Lidarr",
        subtitle="Sync curated exact albums with Lidarr",
        note=f"Mode: {monitor_type}",
        hint="Hint: Use `--quality` to specify a quality profile",
    )

    api_key = os.getenv("LIDARR_API_KEY")
    if not api_key:
        raise click.ClickException(
            "LIDARR_API_KEY is not set. Export it and retry this command.",
        )

    try:
        from minkdb.publish import _catalog_for_publish

        targets = _catalog_for_publish(library_path)
        if not targets:
            raise click.ClickException(
                "No matched albums were found in .minkdb/album.json to publish.",
            )

        unique_artists = {
            e.artist_musicbrainz_id for e in targets if e.artist_musicbrainz_id
        }
        total_items = len(unique_artists) + (
            0 if monitor_type == "all" else len(targets)
        )

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Publishing to Lidarr ({monitor_type} mode)",
                total=total_items,
            )

            def on_artist_added(artist_name: str) -> None:
                progress.update(
                    task, advance=1, description=f"Added artist: {artist_name}"
                )

            def on_album_added(album_name: str) -> None:
                progress.update(
                    task, advance=1, description=f"Added album: {album_name}"
                )

            summary = publish_to_lidarr(
                library_path=library_path,
                lidarr_url=lidarr_url,
                api_key=api_key,
                monitor_type=monitor_type,
                quality_profile=quality_profile,
                on_artist_added=on_artist_added,
                on_album_added=on_album_added,
            )
    except PublishError as exc:
        raise click.ClickException(str(exc)) from exc

    console.print("[bold green]Publish complete[/bold green]")
    console.print(
        "Published: "
        f"{summary.total_albums} album targets | "
        f"{summary.artists_added} artists added | "
        f"{summary.albums_added} albums added | "
        f"{summary.albums_already_present} already present",
    )


if __name__ == "__main__":
    main()
