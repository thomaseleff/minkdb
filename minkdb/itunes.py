"""iTunes XML parser for Mink-db."""

import plistlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Track:
    """Represents an iTunes track."""

    track_id: int
    name: str
    artist: str | None
    album: str | None
    track_number: int | None
    disc_number: int | None
    year: int | None
    location: str | None


def parse_itunes_xml(xml_path: Path) -> list[Track]:
    """Parse iTunes Music Library.xml and return list of tracks."""
    with open(xml_path, "rb") as f:
        data = plistlib.load(f)

    tracks_dict = data.get("Tracks", {})
    tracks: list[Track] = []

    for track_id_str, track_data in tracks_dict.items():
        track_id = int(track_id_str)
        name = track_data.get("Name")
        if not name:
            continue

        artist = track_data.get("Artist")
        album = track_data.get("Album")
        track_number = track_data.get("Track Number")
        disc_number = track_data.get("Disc Number")
        year = track_data.get("Year")
        location = track_data.get("Location")

        tracks.append(
            Track(
                track_id=track_id,
                name=name,
                artist=artist,
                album=album,
                track_number=track_number,
                disc_number=disc_number,
                year=year,
                location=location,
            )
        )

    return tracks


def get_unique_albums(tracks: list[Track]) -> list[tuple[str | None, str | None]]:
    """Get unique (artist, album) pairs from tracks."""
    seen: set[tuple[str | None, str | None]] = set()
    unique: list[tuple[str | None, str | None]] = []

    for track in tracks:
        key = (track.artist, track.album)
        if key not in seen and track.album:
            seen.add(key)
            unique.append(key)

    return unique


def find_itunes_xml(
    library_path: Path,
    filename: str = "iTunes Music Library.xml",
) -> Path | None:
    """Find iTunes XML file in the given path."""
    xml_path = library_path / filename
    if xml_path.exists():
        return xml_path
    return None
