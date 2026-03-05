# Mink-db

A metadata-link between iTunes and MusicBrainz. A CLI tool that catalogs a music library by scanning iTunes libraries and retrieving MusicBrainz artist IDs.

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

Mink-db outputs a JSON array of unique matched MusicBrainz artist IDs:

```json
[
  {"MusicBrainzArtistId": "11111111-1111-1111-1111-111111111111"},
  {"MusicBrainzArtistId": "22222222-2222-2222-2222-222222222222"}
]
```

## How It Works

1. **Reads iTunes XML**: Parses `iTunes Music Library.xml` for album metadata
2. **Deduplicates**: Groups tracks by (artist, album) to avoid duplicate queries
3. **Queries MusicBrainz**: Searches release groups using exact artist + album matching
4. **Caches Results**: Stores album and artist data in `.minkdb/album.json` and `.minkdb/artist.json`
5. **Outputs**: Prints matched IDs to stdout or file

On subsequent runs, Mink-db will skip already-matched albums and only query MusicBrainz for new ones.

## Data Storage

- **Album database**: `<library_path>/.minkdb/album.json`
- **Artist database**: `<library_path>/.minkdb/artist.json` (unique by artist MusicBrainz ID)
- **Album FK**: Each album row includes `artist_musicbrainz_id` referencing `artist.json`

## Requirements

- Python 3.13+
- iTunes Music Library.xml file
- Internet connection (for MusicBrainz queries)
