"""MusicBrainz client for Mink-db."""

import time
from dataclasses import dataclass

import musicbrainzngs
from musicbrainzngs import MusicBrainzError, ResponseError, WebServiceError

from minkdb import __version__

musicbrainzngs.set_useragent("minkdb", __version__)
musicbrainzngs.set_rate_limit(limit_or_interval=True)

MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0


@dataclass
class ReleaseGroupMatch:
    """Search result containing release group and artist identifiers."""

    release_group_id: str | None
    artist_musicbrainz_id: str | None


def _extract_artist_musicbrainz_id(release_group: dict) -> str | None:
    """Extract artist MusicBrainz ID from a release-group result."""
    artist_credit = release_group.get("artist-credit", [])
    if not artist_credit:
        return None

    first_credit = artist_credit[0]
    if not isinstance(first_credit, dict):
        return None

    artist = first_credit.get("artist")
    if not isinstance(artist, dict):
        return None

    artist_id = artist.get("id")
    if isinstance(artist_id, str):
        return artist_id
    return None


def search_release_group_match(artist: str, album: str) -> ReleaseGroupMatch:
    """Search for release group and artist MBIDs for an artist/album pair."""
    if not artist or not album:
        return ReleaseGroupMatch(None, None)

    backoff = INITIAL_BACKOFF

    for attempt in range(MAX_RETRIES):
        try:
            result = musicbrainzngs.search_release_groups(
                query=album,
                artist=artist,
                limit=5,
            )
            release_groups = result.get("release-group-list", [])

            selected_release_group: dict | None = None

            for rg in release_groups:
                if rg.get("title", "").lower() == album.lower():
                    selected_release_group = rg
                    break

            if selected_release_group is None and release_groups:
                selected_release_group = release_groups[0]

            if selected_release_group is None:
                return ReleaseGroupMatch(None, None)

            release_group_id = selected_release_group.get("id")
            if not isinstance(release_group_id, str):
                release_group_id = None

            return ReleaseGroupMatch(
                release_group_id=release_group_id,
                artist_musicbrainz_id=_extract_artist_musicbrainz_id(
                    selected_release_group,
                ),
            )
        except (WebServiceError, ResponseError, MusicBrainzError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(backoff)
                backoff *= 2

    return ReleaseGroupMatch(None, None)


def search_release_group(artist: str, album: str) -> str | None:
    """Search for a release group by artist and album name.

    Returns the Release Group ID (MBID) if found, None otherwise.
    Implements retry with exponential backoff on failure.
    """
    return search_release_group_match(artist, album).release_group_id
