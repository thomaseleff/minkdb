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

### Publish Command

| Option | Alias | Description | Default |
|--------|-------|-------------|---------|
| `--path` | `-p` | Path to iTunes library containing `.minkdb/album.json` | Required |
| `--url` | | Lidarr server URL | `http://localhost:8686` |

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

# Publish curated exact albums to Lidarr
LIDARR_API_KEY="<your-api-key>" uv run python -m minkdb publish --path "M:\Music\iTunes"

# Publish to a non-default Lidarr URL
LIDARR_API_KEY="<your-api-key>" uv run python -m minkdb publish --path "M:\Music\iTunes" --url "http://lidarr.local:8686"
```

### Output

The CLI outputs a JSON array of unique matched MusicBrainz artist IDs:

```json
[
  {"MusicBrainzArtistId": "11111111-1111-1111-1111-111111111111"},
  {"MusicBrainzArtistId": "22222222-2222-2222-2222-222222222222"}
]
```

### Data Storage

- **User settings**: `~/.minkdb/settings.json`
- **Album database**: `<library_path>/.minkdb/album.json`
- **Artist database**: `<library_path>/.minkdb/artist.json` (unique by artist MusicBrainz ID)

### Lidarr Publish Behavior

- Reads matched entries from `.minkdb/album.json`
- Requires `LIDARR_API_KEY` to be set
- Adds artists with broad monitoring disabled
- Monitors only exact albums represented in Mink-db catalog
