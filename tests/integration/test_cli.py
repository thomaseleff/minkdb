"""Integration tests for Mink-db CLI."""

import json

import pytest
from click.testing import CliRunner

import minkdb.cli as cli_module
from minkdb.cli import main
from minkdb.database import (
    AlbumEntry,
    get_album_database_path,
    get_artist_database_path,
    load_artists,
    load_catalog,
    save_catalog,
)
from minkdb.publish import PublishError, PublishSummary


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for tests."""
    return CliRunner()


@pytest.fixture
def temp_library(tmp_path):
    """Provide a temporary library directory with .minkdb folder."""
    mink_dir = tmp_path / ".minkdb"
    mink_dir.mkdir()
    return tmp_path


@pytest.fixture
def itunes_xml_with_track(tmp_path):
    """Provide a minimal iTunes XML file with one track."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Tracks</key>
    <dict>
        <key>1</key>
        <dict>
            <key>Track ID</key><integer>1</integer>
            <key>Name</key><string>Test Song</string>
            <key>Artist</key><string>Test Artist</string>
            <key>Album</key><string>Test Album</string>
        </dict>
    </dict>
</dict>
</plist>"""
    xml_path = tmp_path / "iTunes Music Library.xml"
    xml_path.write_text(xml_content)
    return xml_path


def test_cli_help_shows_options(cli_runner):
    """User expects CLI to show available options."""
    result = cli_runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--path" in result.output
    assert "--itunes" in result.output
    assert "--output" in result.output
    assert "--limit" in result.output
    assert "publish" in result.output


def test_cli_path_not_found(cli_runner):
    """User expects error when path does not exist."""
    result = cli_runner.invoke(main, ["--path", "/nonexistent/path"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_cli_missing_itunes_file(cli_runner, temp_library):
    """User expects error when iTunes XML not found."""
    result = cli_runner.invoke(main, ["--path", str(temp_library)])
    assert result.exit_code == 1
    assert "Could not find" in result.output


def test_cli_outputs_json_format(cli_runner, temp_library, itunes_xml_with_track):
    """User expects JSON output when running catalog."""
    result = cli_runner.invoke(main, ["--path", str(temp_library), "--limit", "1"])
    assert result.exit_code == 0


def test_database_path_includes_mink_folder(temp_library):
    """User expects album database in .minkdb subfolder."""
    db_path = get_album_database_path(temp_library)
    assert db_path.parent.name == ".minkdb"
    assert db_path.name == "album.json"


@pytest.mark.parametrize("entries,expected_count", [
    pytest.param(
        [
            AlbumEntry(
                artist="Test Artist",
                album="Test Album",
                musicbrainz_id="test-id-123",
                matched_at="2026-02-28T15:26:42.221253+00:00",
                status="matched",
                artist_musicbrainz_id="artist-id-123",
            ),
        ],
        1,
        id="single_entry",
    ),
    pytest.param(
        [
            AlbumEntry(
                artist="Artist 1",
                album="Album 1",
                musicbrainz_id="id-1",
                matched_at="2026-02-28T15:26:42.221253+00:00",
                status="matched",
                artist_musicbrainz_id="artist-id-1",
            ),
            AlbumEntry(
                artist="Artist 2",
                album="Album 2",
                musicbrainz_id="id-2",
                matched_at="2026-02-28T15:26:43.000000+00:00",
                status="matched",
                artist_musicbrainz_id="artist-id-2",
            ),
        ],
        2,
        id="multiple_entries",
    ),
])
def test_catalog_persists_across_operations(temp_library, entries, expected_count):
    """User expects catalog to persist when saving and loading."""
    save_catalog(entries, temp_library)
    loaded = load_catalog(temp_library)
    assert len(loaded) == expected_count


def test_load_catalog_empty_when_no_database(temp_library):
    """User expects empty catalog when no database exists."""
    loaded = load_catalog(temp_library)
    assert loaded == []


def test_catalog_output_returns_unique_artist_ids(
    cli_runner,
    temp_library,
    itunes_xml_with_track,
):
    """User expects output to include unique matched artist MusicBrainz IDs only."""
    catalog_file = temp_library / ".minkdb" / "album.json"
    catalog_file.write_text(json.dumps([
        {
            "artist": "Test Artist",
            "album": "Test Album",
            "musicbrainz_id": "e12e9e4e-8c2f-3682-92e9-3b5240065abb",
            "matched_at": "2026-02-28T15:26:42.221253+00:00",
            "status": "matched",
            "artist_musicbrainz_id": "11111111-1111-1111-1111-111111111111",
        },
        {
            "artist": "Test Artist",
            "album": "Another Album",
            "musicbrainz_id": "f22e9e4e-8c2f-3682-92e9-3b5240065abf",
            "matched_at": "2026-02-28T15:26:43.221253+00:00",
            "status": "matched",
            "artist_musicbrainz_id": "11111111-1111-1111-1111-111111111111",
        },
        {
            "artist": "Unknown",
            "album": "Unknown",
            "musicbrainz_id": None,
            "matched_at": None,
            "status": "unmatched",
            "artist_musicbrainz_id": None,
        },
    ]))

    output_path = temp_library / "ids.json"
    result = cli_runner.invoke(
        main,
        ["--path", str(temp_library), "--output", str(output_path)],
    )
    assert result.exit_code == 0
    payload = json.loads(output_path.read_text())
    assert payload == [
        {"MusicBrainzArtistId": "11111111-1111-1111-1111-111111111111"},
    ]


def test_artist_database_path_includes_mink_folder(temp_library):
    """User expects artist database in .minkdb subfolder."""
    db_path = get_artist_database_path(temp_library)
    assert db_path.parent.name == ".minkdb"
    assert db_path.name == "artist.json"


def test_artist_json_unique_by_musicbrainz_id(temp_library):
    """User expects artist.json to contain unique artist MBIDs only."""
    entries = [
        AlbumEntry(
            artist="ABBA",
            album="Gold",
            musicbrainz_id="e12e9e4e-8c2f-3682-92e9-3b5240065abb",
            matched_at="2026-02-28T15:26:42.221253+00:00",
            status="matched",
            artist_musicbrainz_id="11111111-1111-1111-1111-111111111111",
        ),
        AlbumEntry(
            artist="ABBA",
            album="Arrival",
            musicbrainz_id="e22e9e4e-8c2f-3682-92e9-3b5240065abc",
            matched_at="2026-02-28T15:26:43.221253+00:00",
            status="matched",
            artist_musicbrainz_id="11111111-1111-1111-1111-111111111111",
        ),
    ]
    save_catalog(entries, temp_library)

    artists = load_artists(temp_library)
    assert len(artists) == 1
    assert artists[0].musicbrainz_id == "11111111-1111-1111-1111-111111111111"


def test_publish_requires_lidarr_api_key(cli_runner, temp_library):
    """User expects a clear error when LIDARR_API_KEY is not set."""
    result = cli_runner.invoke(
        main,
        ["publish", "--path", str(temp_library)],
    )
    assert result.exit_code == 1
    assert "LIDARR_API_KEY is not set" in result.output


def test_publish_invokes_lidarr_workflow(cli_runner, monkeypatch, temp_library):
    """User expects publish command to call the publish workflow."""
    calls = {}

    def fake_publish_to_lidarr(library_path, lidarr_url, api_key):
        calls["library_path"] = library_path
        calls["lidarr_url"] = lidarr_url
        calls["api_key"] = api_key
        return PublishSummary(
            total_albums=2,
            artists_added=1,
            albums_added=1,
            albums_already_present=1,
        )

    monkeypatch.setenv("LIDARR_API_KEY", "test-key")
    monkeypatch.setattr(cli_module, "publish_to_lidarr", fake_publish_to_lidarr)

    result = cli_runner.invoke(
        main,
        [
            "publish",
            "--path",
            str(temp_library),
            "--url",
            "http://lidarr.local:8686",
        ],
    )

    assert result.exit_code == 0
    assert "Publish complete" in result.output
    assert "album targets" in result.output
    assert calls == {
        "library_path": temp_library,
        "lidarr_url": "http://lidarr.local:8686",
        "api_key": "test-key",
    }


def test_publish_shows_publish_error(cli_runner, monkeypatch, temp_library):
    """User expects user-friendly publish errors to bubble through CLI."""

    def fake_publish_to_lidarr(library_path, lidarr_url, api_key):
        raise PublishError("No matched albums were found in .minkdb/album.json.")

    monkeypatch.setenv("LIDARR_API_KEY", "test-key")
    monkeypatch.setattr(cli_module, "publish_to_lidarr", fake_publish_to_lidarr)

    result = cli_runner.invoke(
        main,
        ["publish", "--path", str(temp_library)],
    )

    assert result.exit_code == 1
    assert "No matched albums were found" in result.output
