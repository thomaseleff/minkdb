"""Lidarr publish workflow for curated exact-album sync."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from minkdb.database import AlbumEntry, load_catalog


@dataclass
class PublishSummary:
    """Summary of a publish run."""

    total_albums: int
    artists_added: int
    albums_added: int
    albums_already_present: int


class PublishError(Exception):
    """User-facing publish failure."""


def _to_dict(value: Any) -> dict[str, Any]:
    """Best-effort conversion for lidarr model objects."""
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "to_dict"):
        as_dict = value.to_dict()
        if isinstance(as_dict, dict):
            return as_dict
    if hasattr(value, "__dict__"):
        return {
            key: raw
            for key, raw in vars(value).items()
            if not key.startswith("_")
        }
    return {}


def _normalize_url(url: str) -> str:
    """Normalize Lidarr base URL."""
    normalized = url.strip().rstrip("/")
    if not normalized:
        raise PublishError("Lidarr URL cannot be empty.")
    return normalized


def _catalog_for_publish(library_path: Path) -> list[AlbumEntry]:
    """Return matched catalog entries with both album and artist MBIDs."""
    entries = load_catalog(library_path)
    filtered: list[AlbumEntry] = []
    seen_album_ids: set[str] = set()

    for entry in entries:
        if not entry.musicbrainz_id or not entry.artist_musicbrainz_id:
            continue
        if entry.musicbrainz_id in seen_album_ids:
            continue
        seen_album_ids.add(entry.musicbrainz_id)
        filtered.append(entry)

    return filtered


def _import_lidarr() -> Any:
    """Import lidarr-py lazily so non-publish flows do not require it."""
    try:
        lidarr = importlib.import_module("lidarr")
    except ImportError as exc:
        raise PublishError(
            "Missing dependency `lidarr-py`. Install dependencies and retry publish.",
        ) from exc
    return lidarr


def _first_id(values: list[Any]) -> int | None:
    """Extract the first integer `id` from a list of model objects."""
    for value in values:
        value_id = _to_dict(value).get("id")
        if isinstance(value_id, int):
            return value_id
    return None


def _first_root_folder(values: list[Any]) -> str | None:
    """Extract the first root folder path from a list of model objects."""
    for value in values:
        path = _to_dict(value).get("path")
        if isinstance(path, str) and path:
            return path
    return None


def _validate_uuid(value: str, label: str) -> UUID:
    """Parse UUID and raise a friendly error when invalid."""
    try:
        return UUID(value)
    except ValueError as exc:
        raise PublishError(f"Invalid {label} UUID: {value}") from exc


def _ensure_artist(
    lidarr: Any,
    api_client: Any,
    artist_musicbrainz_id: str,
    artist_name: str,
    default_quality_profile_id: int,
    default_metadata_profile_id: int,
    default_root_folder_path: str,
) -> tuple[int, bool]:
    """Ensure a Lidarr artist exists and return (artist_id, created)."""
    artist_api = lidarr.ArtistApi(api_client)
    artist_lookup_api = lidarr.ArtistLookupApi(api_client)

    existing = artist_api.list_artist(
        mb_id=_validate_uuid(artist_musicbrainz_id, "artist_musicbrainz_id"),
    )
    if existing:
        existing_id = _to_dict(existing[0]).get("id")
        if isinstance(existing_id, int):
            return existing_id, False

    lookup_results = artist_lookup_api.list_artist_lookup(
        term=f"lidarr:{artist_musicbrainz_id}",
    )
    if not lookup_results:
        raise PublishError(
            f"Artist lookup failed for {artist_name} ({artist_musicbrainz_id}).",
        )

    selected = None
    for candidate in lookup_results:
        candidate_dict = _to_dict(candidate)
        candidate_mbid = candidate_dict.get("foreign_artist_id")
        if candidate_mbid == artist_musicbrainz_id:
            selected = candidate_dict
            break
    if selected is None:
        selected = _to_dict(lookup_results[0])

    selected.pop("id", None)
    selected["foreign_artist_id"] = artist_musicbrainz_id
    selected["monitored"] = False
    selected["quality_profile_id"] = selected.get(
        "quality_profile_id",
        default_quality_profile_id,
    )
    selected["metadata_profile_id"] = selected.get(
        "metadata_profile_id",
        default_metadata_profile_id,
    )
    selected["root_folder_path"] = selected.get(
        "root_folder_path",
        default_root_folder_path,
    )

    add_options = selected.get("add_options")
    if not isinstance(add_options, dict):
        add_options = {}
    add_options["monitor"] = "none"
    add_options["search_for_missing_albums"] = False
    add_options["search_for_missing_tracks"] = False
    selected["add_options"] = add_options

    created = artist_api.create_artist(artist_resource=selected)
    created_id = _to_dict(created).get("id")
    if not isinstance(created_id, int):
        raise PublishError(
            f"Artist add returned no Lidarr id for {artist_name} "
            f"({artist_musicbrainz_id}).",
        )
    return created_id, True


def _ensure_album(
    lidarr: Any,
    api_client: Any,
    artist_id: int,
    album_musicbrainz_id: str,
    artist_name: str,
    album_name: str,
    default_quality_profile_id: int,
) -> tuple[bool, bool]:
    """Ensure exact album exists and is monitored.

    Returns (created, already_present).
    """
    album_api = lidarr.AlbumApi(api_client)
    album_lookup_api = lidarr.AlbumLookupApi(api_client)

    existing = album_api.list_album(foreign_album_id=album_musicbrainz_id)
    if existing:
        existing_ids = []
        for candidate in existing:
            candidate_id = _to_dict(candidate).get("id")
            if isinstance(candidate_id, int):
                existing_ids.append(candidate_id)
        if existing_ids:
            album_api.put_album_monitor(
                albums_monitored_resource={
                    "album_ids": existing_ids,
                    "monitored": True,
                },
            )
            return False, True

    lookup_results = album_lookup_api.list_album_lookup(
        term=f"lidarr:{album_musicbrainz_id}",
    )
    if not lookup_results:
        raise PublishError(
            f"Album lookup failed for {artist_name} - {album_name} "
            f"({album_musicbrainz_id}).",
        )

    selected = None
    for candidate in lookup_results:
        candidate_dict = _to_dict(candidate)
        candidate_album_mbid = candidate_dict.get("foreign_album_id")
        if candidate_album_mbid == album_musicbrainz_id:
            selected = candidate_dict
            break
    if selected is None:
        selected = _to_dict(lookup_results[0])

    selected.pop("id", None)
    selected["foreign_album_id"] = album_musicbrainz_id
    selected["artist_id"] = artist_id
    selected["monitored"] = True
    selected["quality_profile_id"] = selected.get(
        "quality_profile_id",
        default_quality_profile_id,
    )

    add_options = selected.get("add_options")
    if not isinstance(add_options, dict):
        add_options = {}
    add_options["search_for_new_album"] = False
    selected["add_options"] = add_options

    album_api.create_album(album_resource=selected)
    return True, False


def publish_to_lidarr(
    library_path: Path,
    lidarr_url: str,
    api_key: str,
) -> PublishSummary:
    """Publish curated matched albums from Mink-db to Lidarr."""
    targets = _catalog_for_publish(library_path)
    if not targets:
        raise PublishError(
            "No matched albums were found in .minkdb/album.json to publish.",
        )

    lidarr = _import_lidarr()
    configuration = lidarr.Configuration(host=_normalize_url(lidarr_url))
    configuration.api_key["apikey"] = api_key
    configuration.api_key["X-Api-Key"] = api_key

    artists_added = 0
    albums_added = 0
    albums_already_present = 0

    with lidarr.ApiClient(configuration) as api_client:
        quality_profile_api = lidarr.QualityProfileApi(api_client)
        metadata_profile_api = lidarr.MetadataProfileApi(api_client)
        root_folder_api = lidarr.RootFolderApi(api_client)

        quality_profile_id = _first_id(quality_profile_api.list_quality_profile())
        metadata_profile_id = _first_id(metadata_profile_api.list_metadata_profile())
        root_folder_path = _first_root_folder(root_folder_api.list_root_folder())

        if quality_profile_id is None:
            raise PublishError("Lidarr has no quality profile configured.")
        if metadata_profile_id is None:
            raise PublishError("Lidarr has no metadata profile configured.")
        if root_folder_path is None:
            raise PublishError("Lidarr has no root folder configured.")

        artist_ids: dict[str, int] = {}
        for entry in targets:
            assert entry.artist_musicbrainz_id
            artist_mbid = entry.artist_musicbrainz_id

            if artist_mbid not in artist_ids:
                artist_id, created = _ensure_artist(
                    lidarr=lidarr,
                    api_client=api_client,
                    artist_musicbrainz_id=artist_mbid,
                    artist_name=entry.artist,
                    default_quality_profile_id=quality_profile_id,
                    default_metadata_profile_id=metadata_profile_id,
                    default_root_folder_path=root_folder_path,
                )
                artist_ids[artist_mbid] = artist_id
                if created:
                    artists_added += 1

            assert entry.musicbrainz_id
            created, already_present = _ensure_album(
                lidarr=lidarr,
                api_client=api_client,
                artist_id=artist_ids[artist_mbid],
                album_musicbrainz_id=entry.musicbrainz_id,
                artist_name=entry.artist,
                album_name=entry.album,
                default_quality_profile_id=quality_profile_id,
            )
            if created:
                albums_added += 1
            if already_present:
                albums_already_present += 1

    return PublishSummary(
        total_albums=len(targets),
        artists_added=artists_added,
        albums_added=albums_added,
        albums_already_present=albums_already_present,
    )
