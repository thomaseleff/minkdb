"""JSON database for Mink-db album and artist catalogs."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AlbumEntry:
    """Represents an album entry in the album catalog."""

    artist: str
    album: str
    musicbrainz_id: str | None
    matched_at: str | None
    status: str
    artist_musicbrainz_id: str | None = None


@dataclass
class ArtistEntry:
    """Represents an artist entry in the artist catalog."""

    musicbrainz_id: str
    artist: str


def get_database_dir(library_path: Path | None) -> Path:
    """Get the database directory for the library."""
    if library_path is None:
        library_path = Path.cwd()
    else:
        library_path = Path(library_path)
    db_dir = library_path / ".minkdb"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir


def get_album_database_path(library_path: Path | None) -> Path:
    """Get the album database path for the library."""
    return get_database_dir(library_path) / "album.json"


def get_artist_database_path(library_path: Path | None) -> Path:
    """Get the artist database path for the library."""
    return get_database_dir(library_path) / "artist.json"


def load_catalog(library_path: Path | None) -> list[AlbumEntry]:
    """Load the album catalog from the JSON database."""
    db_path = get_album_database_path(library_path)
    if not db_path.exists():
        return []

    with open(db_path) as f:
        data = json.load(f)

    return [AlbumEntry(**entry) for entry in data]


def save_catalog(entries: list[AlbumEntry], library_path: Path | None) -> None:
    """Save the album catalog to the JSON database."""
    db_path = get_album_database_path(library_path)
    with open(db_path, "w") as f:
        json.dump([asdict(e) for e in entries], f, indent=2)

    artists_by_id: dict[str, ArtistEntry] = {}
    for entry in entries:
        if entry.artist_musicbrainz_id:
            artists_by_id[entry.artist_musicbrainz_id] = ArtistEntry(
                musicbrainz_id=entry.artist_musicbrainz_id,
                artist=entry.artist,
            )

    save_artists(list(artists_by_id.values()), library_path)


def load_artists(library_path: Path | None) -> list[ArtistEntry]:
    """Load the artist catalog from the JSON database."""
    db_path = get_artist_database_path(library_path)
    if not db_path.exists():
        return []

    with open(db_path) as f:
        data = json.load(f)

    return [ArtistEntry(**entry) for entry in data]


def save_artists(entries: list[ArtistEntry], library_path: Path | None) -> None:
    """Save the artist catalog to the JSON database."""
    db_path = get_artist_database_path(library_path)
    with open(db_path, "w") as f:
        json.dump([asdict(e) for e in entries], f, indent=2)


def upsert_artist(entry: ArtistEntry, library_path: Path | None) -> None:
    """Upsert a unique artist by MusicBrainz ID."""
    artists = load_artists(library_path)

    for i, artist in enumerate(artists):
        if artist.musicbrainz_id == entry.musicbrainz_id:
            artists[i] = entry
            break
    else:
        artists.append(entry)

    save_artists(artists, library_path)


def append_to_catalog(entry: AlbumEntry, library_path: Path | None) -> None:
    """Append a single entry to the album catalog (append-only)."""
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
    """Find an album in the album catalog."""
    entries = load_catalog(library_path)
    for entry in entries:
        if entry.artist == artist and entry.album == album:
            return entry
    return None
