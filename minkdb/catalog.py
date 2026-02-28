"""Catalog orchestration for Mink-db."""

from datetime import datetime, timezone
from pathlib import Path

from minkdb.database import AlbumEntry, append_to_catalog, load_catalog
from minkdb.itunes import Track, find_itunes_xml, parse_itunes_xml
from minkdb.musicbrainz import search_release_group


def find_and_parse_itunes(
    library_path: Path,
    itunes_filename: str = "iTunes Music Library.xml",
) -> Path:
    """Find iTunes XML file and return its path."""
    xml_path = find_itunes_xml(library_path, itunes_filename)
    if xml_path is None:
        raise FileNotFoundError(f"Could not find {itunes_filename} in {library_path}")
    return xml_path


def parse_tracks(xml_path: Path) -> list[Track]:
    """Parse tracks from iTunes XML."""
    return parse_itunes_xml(xml_path)


def get_unique_albums(tracks: list[Track]) -> list[tuple[str, str]]:
    """Get unique (artist, album) pairs from tracks."""
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []

    for track in tracks:
        if track.artist and track.album:
            key = (track.artist, track.album)
            if key not in seen:
                seen.add(key)
                unique.append(key)

    return unique


def load_existing_catalog(library_path: Path) -> list[AlbumEntry]:
    """Load existing catalog from database."""
    return load_catalog(library_path)


def process_albums(
    unique_albums: list[tuple[str, str]],
    existing_catalog: list[AlbumEntry],
    library_path: Path,
    limit: int | None = None,
) -> list[AlbumEntry]:
    """Process albums and query MusicBrainz for missing matches."""
    existing = {(e.artist, e.album): e for e in existing_catalog}

    albums_to_process = unique_albums
    if limit:
        albums_to_process = albums_to_process[:limit]

    results: list[AlbumEntry] = []

    for artist, album in albums_to_process:
        if (artist, album) in existing:
            entry = existing[(artist, album)]
        else:
            mbid = search_release_group(artist, album)
            timestamp = datetime.now().replace(tzinfo=timezone.utc).isoformat()
            entry = AlbumEntry(
                artist=artist,
                album=album,
                musicbrainz_id=mbid,
                matched_at=timestamp if mbid else None,
                status="matched" if mbid else "unmatched",
            )
            append_to_catalog(entry, library_path)

        results.append(entry)

    return results


def get_catalog_output(entries: list[AlbumEntry]) -> list[dict]:
    """Generate the output list of matched MusicBrainz IDs."""
    output = []
    for entry in entries:
        if entry.musicbrainz_id:
            output.append({"MusicBrainzId": entry.musicbrainz_id})
    return output
