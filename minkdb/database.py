"""JSON database for Mink-db catalog."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AlbumEntry:
    """Represents an album entry in the catalog."""

    artist: str
    album: str
    musicbrainz_id: str | None
    matched_at: str | None
    status: str


def get_database_path(library_path: Path | None) -> Path:
    """Get the database path for the library."""
    if library_path is None:
        library_path = Path.cwd()
    else:
        library_path = Path(library_path)
    db_dir = library_path / ".minkdb"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "catalog.json"


def load_catalog(library_path: Path | None) -> list[AlbumEntry]:
    """Load the catalog from the JSON database."""
    db_path = get_database_path(library_path)
    if not db_path.exists():
        return []

    with open(db_path) as f:
        data = json.load(f)

    return [AlbumEntry(**entry) for entry in data]


def save_catalog(entries: list[AlbumEntry], library_path: Path | None) -> None:
    """Save the catalog to the JSON database."""
    db_path = get_database_path(library_path)
    with open(db_path, "w") as f:
        json.dump([asdict(e) for e in entries], f, indent=2)


def append_to_catalog(entry: AlbumEntry, library_path: Path | None) -> None:
    """Append a single entry to the catalog (append-only)."""
    entries = load_catalog(library_path)

    for i, e in enumerate(entries):
        if e.artist == entry.artist and e.album == entry.album:
            entries[i] = entry
            break
    else:
        entries.append(entry)

    save_catalog(entries, library_path)


def find_in_catalog(
    artist: str,
    album: str,
    library_path: Path | None,
) -> AlbumEntry | None:
    """Find an album in the catalog."""
    entries = load_catalog(library_path)
    for entry in entries:
        if entry.artist == artist and entry.album == album:
            return entry
    return None
