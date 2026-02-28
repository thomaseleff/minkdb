"""MusicBrainz client for Mink-db."""

import time

import musicbrainzngs
from musicbrainzngs import MusicBrainzError, ResponseError, WebServiceError

from minkdb import __version__

musicbrainzngs.set_useragent("minkdb", __version__)
musicbrainzngs.set_rate_limit(limit_or_interval=True)

MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0


def search_release_group(artist: str, album: str) -> str | None:
    """Search for a release group by artist and album name.

    Returns the Release Group ID (MBID) if found, None otherwise.
    Implements retry with exponential backoff on failure.
    """
    if not artist or not album:
        return None

    backoff = INITIAL_BACKOFF

    for attempt in range(MAX_RETRIES):
        try:
            result = musicbrainzngs.search_release_groups(
                query=album,
                artist=artist,
                limit=5,
            )
            release_groups = result.get("release-group-list", [])

            for rg in release_groups:
                if rg.get("title", "").lower() == album.lower():
                    return rg.get("id")

            if release_groups:
                return release_groups[0].get("id")

            return None
        except (WebServiceError, ResponseError, MusicBrainzError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(backoff)
                backoff *= 2

    return None
