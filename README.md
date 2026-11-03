# Ultimate Guitar → Spotify playlist

A small command-line tool and Claude plugin for creating private, source-ordered Spotify playlists from song-list CSVs. It accepts lists from any source with a title/track/song column and an optional artist/performer/band column; it can also convert a text-based Ultimate Guitar “My Tabs” PDF export to CSV. It does not access Ultimate Guitar or scrape a logged-in browser session: provide an export you obtained yourself.

## Requirements

- Python 3.10+
- A Spotify account and a Spotify developer app

Create a Spotify developer app at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard). Add the redirect URI `http://127.0.0.1:8888/callback` in the app settings. Set the credentials in your shell (never commit them):

```sh
export SPOTIPY_CLIENT_ID="your-client-id"
export SPOTIPY_CLIENT_SECRET="your-client-secret"
export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8888/callback"
```

The app uses Spotify OAuth and requests only playlist modification scopes. Spotipy keeps the token cache under `~/.cache/ug-spotify-playlist/`; do not share that file.

## Install

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install .
```

### Claude Code plugin, skill, and MCP server

This repository is also packaged as a Claude Code plugin containing a reusable skill and the MCP tools. Install `uv`, then add the public GitHub repo as a Claude Code marketplace and install the plugin:

```sh
claude plugin marketplace add joshikhajan/ultimate-guitar-spotify-playlist
claude plugin install spotify-playlist-builder@spotify-playlist-tools
```

The installed skill is `/spotify-playlist-builder:spotify-playlist`. The MCP server starts locally over stdio using `uv`; configure the Spotify developer app environment variables from above in Claude Code's environment. Tools are named `convert_ultimate_guitar_pdf`, `preview_spotify_matches`, and `create_spotify_playlist`. Preview is read-only; playlist creation requires the preview ID and `confirm_create=true`, and always creates a new private playlist. Claude Code may ask you to trust the marketplace/plugin before it enables components.

To install the skill without enabling MCP, copy `skills/spotify-playlist/` to `~/.claude/skills/spotify-playlist/`.

The repo is public and installable directly as a marketplace. For listing in Anthropic's central Claude directory (which also makes it available via claude.ai/Cowork), the maintainer must submit the plugin through [Claude's developer directory portal](https://claude.ai/directory/manage) and satisfy its account and review requirements.

## Convert PDF export to CSV

```sh
ug-tabs-pdf-to-csv path/to/ultimate-guitar-my-tabs.pdf
```

By default this creates a sibling CSV with the same base filename. To choose another path:

```sh
ug-tabs-pdf-to-csv path/to/ultimate-guitar-my-tabs.pdf --output favorites.csv
```

The converter is intended for text-based PDFs saved from the Ultimate Guitar My Tabs page. It preserves source order and outputs `title,artist,saved_date,tab_type`. If the PDF is scanned or its table layout differs, conversion fails instead of silently claiming success; use OCR or correct the CSV manually in that case.

## Preview and review from any song CSV

Songs are processed in CSV order. Supported title headers are `title`, `track`, `song`, `track name`, and `song title`; supported optional artist headers are `artist`, `performer`, and `band`. When the artist column contains a generic category such as “Misc Soundtrack,” it is ignored; a title shaped like `Artist - Song` is split when appropriate.

```sh
ug-spotify-playlist path/to/favorites.csv
```

The default is preview-only. It prints counts and writes `matches.csv` for review. High-confidence matches are included; ambiguous or unmatched entries are not guessed. Identical Spotify track IDs are only added once, keeping the first source occurrence.

Inspect the report, correct the source CSV if needed, and rerun with the explicit `--apply` flag to create a new **private** playlist:

```sh
ug-spotify-playlist path/to/favorites.csv \
  --playlist "Ultimate Guitar" \
  --report review.csv \
  --apply
```

Use `--public` only if you explicitly want the new playlist to be public. The tool creates a new playlist; it does not edit or delete existing playlists. Review the report before applying, especially for ambiguous songs and alternate versions.

## Development

```sh
python -m pip install -e '.[test]'
pytest
```

## Privacy

The CSV and report remain on your computer. This tool sends song title/artist search queries to Spotify and creates a playlist only when `--apply` is passed. Never publish your CSV export, Spotify credentials, or token cache.
