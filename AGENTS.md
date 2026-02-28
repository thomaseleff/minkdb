# Mink-db

A metadata-link between iTunes and MusicBrainz. A CLI tool that catalogs a music library by scanning iTunes libraries and retrieving MusicBrainz IDs.

## Developer Instructions

### Setup

```bash
uv sync
```

### Linting

```bash
uv run ruff check .
```

### Type Checking

```bash
uv run ty check .
```

### Running the CLI

```bash
uv run python -m minkdb --help
```

### Adding Dependencies

```bash
uv add <package>
```

### Testing

See [tests/AGENTS.md](tests/AGENTS.md) for testing guidelines.

```bash
# Run all tests
uv run pytest tests/

# Run integration tests only
uv run pytest tests/integration/
```

## CLI Reference

### Options

| Option | Alias | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Path to iTunes library (defaults to cwd) | Current directory |
| `--itunes` | `-i` | iTunes XML filename to search for | `iTunes Music Library.xml` |
| `--output` | `-o` | Output file path | stdout |
| `--limit` | `-l` | Limit number of albums to process | No limit |
| `--rematch` | | Retry matching for unmatched albums | False |
| `--version` | | Show version and exit | |
| `--help` | | Show help message and exit | |

### Examples

```bash
# Default: looks for iTunes Music Library.xml in current directory
uv run python -m minkdb

# Specify iTunes library path
uv run python -m minkdb --path "M:\Music\iTunes"

# Limit to 10 albums
uv run python -m minkdb --path "M:\Music\iTunes" --limit 10

# Output to file
uv run python -m minkdb --path "M:\Music\iTunes" -o ids.json

# Retry matching for previously unmatched albums
uv run python -m minkdb --path "M:\Music\iTunes" --rematch
```

### Output

The CLI outputs a JSON array of matched MusicBrainz IDs:

```json
[
  {"MusicBrainzId": "41656317-c512-456f-9fe7-1f7fb8482a34"},
  {"MusicBrainzId": "8ccd44fb-1c4a-4c5f-98b5-cf3b35a2aa5c"}
]
```

### Data Storage

- **User settings**: `~/.minkdb/settings.json`
- **Library catalog**: `<library_path>/.minkdb/catalog.json` (append-only)
