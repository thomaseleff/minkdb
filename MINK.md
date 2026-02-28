# Project: Mink-db CLI

## Overview

CLI tool that reads iTunes library metadata (XML), queries MusicBrainz for Release Group IDs (album IDs), and outputs a JSON array of MusicBrainz IDs.

## Architecture

```
minkdb/
├── pyproject.toml       # Package config with uv + tool.uv.package = true
├── README.md           # User documentation
├── AGENTS.md           # Developer instructions
├── MINK.md             # This file
├── tests/              # Integration tests
│   └── integration/
└── minkdb/            # Package
    ├── __init__.py
    ├── __main__.py
    ├── cli.py          # Click CLI
    ├── itunes.py       # iTunes XML parser
    ├── musicbrainz.py  # MusicBrainz client
    ├── catalog.py      # Orchestration
    ├── database.py     # JSON catalog
    └── settings.py     # Settings management
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Package name | `minkdb` | `mink` was taken on PyPI |
| CLI name | `mink-db` | User-friendly with hyphen |
| Output IDs | Release Group IDs | User requirement |
| Auth | None (1 req/sec) | YAGNI |
| Matching | Exact only | User requirement |
| Rate limiting | 1 req/second | MusicBrainz requirement |
| Retry logic | 3 retries with exponential backoff | Reliability |
| Rematch | `--rematch` flag for unmatched albums | UX improvement |

## Features

- **Retry with backoff**: MusicBrainz requests retry up to 3 times with exponential backoff on failure
- **Rematch**: `--rematch` flag to retry matching for previously unmatched albums
- **Progress bar**: Visual feedback during album processing
- **Pretty table**: Rich-formatted output in terminal

## Workstreams

| # | Workstream | Status |
|---|------------|--------|
| 1 | Project Setup & CLI Foundation | ✅ Complete |
| 2 | iTunes XML Parser | ✅ Complete |
| 3 | MusicBrainz Client | ✅ Complete |
| 4 | Catalog & Matching | ✅ Complete |
| 5 | Output & Integration | ✅ Complete |
| 6 | Fuzzy Matching | ⏳ Deferred |

### Future: Fuzzy Matching

- Implement fuzzy string matching for artist/album names
- Levenshtein distance or similar
- Confidence scoring
- Handle edge cases (featuring artists, live albums, etc.)

## Acceptance Criteria

1. CLI accepts library path as argument
2. Parses iTunes XML metadata correctly
3. Queries MusicBrainz for Release Group IDs
4. Outputs valid JSON array of unique MusicBrainz IDs
5. Respects rate limiting (1 req/sec)
6. Passes ruff linting and ty type checking
7. Handles errors gracefully (skips unmatched, continues)

## Usage

```bash
# Run directly with uvx
uvx mink-db --path "M:\Music\iTunes"

# Install and run
uv tool install .
mink-db --path "M:\Music\iTunes"
```
