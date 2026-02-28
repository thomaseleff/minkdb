# Mink-db

A metadata-link between iTunes and MusicBrainz. A CLI tool that catalogs a music library by scanning iTunes libraries and retrieving MusicBrainz Release Group IDs.

## How-it-works

1. **Locates your iTunes Library:** Scans a directory for the `iTunes Music Library.xml` file.
2. **Parses Tracks:** Reads and indexes individual track metadata from the XML library.
3. **Aggregates Albums:** Groups tracks into unique album entities based on tags.
4. **References the Catalog:** Compares found albums against the local `./minkdb` database of existing matches.
5. **Reconciles (MusicBrainz):** Queries the MusicBrainz API to link local albums to official IDs.
6. **Generates Output:** Finalizes the metadata-link and updates the local data store.

## Installation

Mink-db requires Python 3.13 or later.

```bash
# Run directly with uvx (no installation required)
uvx minkdb --help

# Or install as a tool
git clone https://github.com/thomaseleff/minkdb.git
cd minkdb
uv tool install .
```

## Quick Start

Catalog your iTunes library and get MusicBrainz IDs:

```bash
minkdb --path "M:\Music\iTunes"
```

## Usage

```bash
# Basic usage (defaults to current directory)
minkdb

# Specify iTunes library path
minkdb --path "M:\Music\iTunes"

# Limit number of albums processed
minkdb --path "M:\Music\iTunes" --limit 10

# Save output to file
minkdb --path "M:\Music\iTunes" -o ids.json

# Retry matching for previously unmatched albums
minkdb --path "M:\Music\iTunes" --rematch
```

## Output Format

Mink-db outputs a JSON array of matched MusicBrainz IDs:

```json
[
  {"MusicBrainzId": "41656317-c512-456f-9fe7-1f7fb8482a34"},
  {"MusicBrainzId": "8ccd44fb-1c4a-4c5f-98b5-cf3b35a2aa5c"}
]
```

## How It Works

1. **Reads iTunes XML**: Parses `iTunes Music Library.xml` for album metadata
2. **Deduplicates**: Groups tracks by (artist, album) to avoid duplicate queries
3. **Queries MusicBrainz**: Searches for Release Group IDs using exact artist + album matching
4. **Caches Results**: Stores results in `.minkdb/catalog.json` (append-only)
5. **Outputs**: Prints matched IDs to stdout or file

On subsequent runs, Mink-db will skip already-matched albums and only query MusicBrainz for new ones.

## Data Storage

- **Catalog database**: `<library_path>/.minkdb/catalog.json`
- **Append-only**: Previous entries are preserved and updated

## Requirements

- Python 3.13+
- iTunes Music Library.xml file
- Internet connection (for MusicBrainz queries)
