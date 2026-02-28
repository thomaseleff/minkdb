# Mink-db Test Guidelines

## Overview

Integration tests for Mink-db should test CLI functions "as a user" - simulating real user interactions with the command-line interface.

## Test Structure

```
tests/
├── AGENTS.md           # This file
└── integration/        # Integration tests
    └── test_cli.py     # CLI integration tests
```

## Guidelines

### Do

- Use function-based tests
- Use module-level imports (all imports at the top of the file)
- Use pytest fixtures for reusable test components
- Use pytest parameterization for testing multiple inputs
- Test CLI behavior as a user would experience it
- Use `click.testing.CliRunner` to invoke CLI commands

### Don't

- Never test private functions (prefixed with `_`)
- Never test Python or dependency behavior (e.g., plistlib, click internals)
- Never use class-based tests
- Never use local/non-module-level imports inside test functions
- Never write unit tests

## Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run integration tests only
uv run pytest tests/integration/

# Run with verbose output
uv run pytest tests/ -v

# Run with fixtures shown
uv run pytest tests/ -v --setup-show
```

## Good Example

```python
"""Integration tests for Mink-db CLI."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from minkdb.cli import main
from minkdb.database import AlbumEntry, get_database_path, load_catalog, save_catalog


# Fixtures at module level
@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for tests."""
    return CliRunner()


@pytest.fixture
def temp_library(tmp_path):
    """Provide a temporary library directory."""
    mink_dir = tmp_path / ".minkdb"
    mink_dir.mkdir()
    return tmp_path


# Parameterized test
@pytest.mark.parametrize("entries,expected_count", [
    pytest.param(
        [
            AlbumEntry(
                artist="Test Artist",
                album="Test Album",
                musicbrainz_id="test-id",
                matched_at="2026-02-28T15:26:42.221253+00:00",
                status="matched",
            ),
        ],
        1,
        id="single_entry",
    ),
    pytest.param(
        [
            AlbumEntry(artist="A", album="A", musicbrainz_id="1", matched_at="", status="matched"),
            AlbumEntry(artist="B", album="B", musicbrainz_id="2", matched_at="", status="matched"),
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


def test_cli_help_shows_options(cli_runner):
    """User expects CLI to show available options."""
    result = cli_runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--path" in result.output
```

## Bad Example

```python
"""Bad test examples - DO NOT USE."""

import pytest
from unittest.mock import patch


# BAD: Local import inside test function
def test_something():
    # DON'T DO THIS - use module-level imports
    from minkdb.database import load_catalog
    ...


# BAD: Tests private function
def test_private_parser_internal():
    """This tests private behavior - DON'T DO THIS."""
    from minkdb.itunes import _parse_track_dict  # Private!
    # ...


# BAD: Tests Python dependency behavior
def test_plistlib_parsing():
    """This tests plistlib, not domain logic - DON'T DO THIS."""
    import plistlib
    data = plistlib.load(...)  # Testing Python internals!
    # ...


# BAD: Class-based test
class TestCLI:
    """Class-based tests - DON'T DO THIS."""
    def test_something(self):
        ...


# BAD: Tests click internals
def test_click_option_decorator():
    """This tests click behavior - DON'T DO THIS."""
    from click import Option
    # ...
```
