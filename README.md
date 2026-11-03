# Ultimate Guitar → Spotify playlist

A small command-line tool that converts a text-based Ultimate Guitar “My Tabs” PDF export to CSV, searches Spotify for likely recordings, and creates a private, source-ordered playlist. It does not access Ultimate Guitar or scrape a logged-in browser session: provide an export you obtained yourself.

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

### MCP and Claude Code

To expose PDF conversion, Spotify match preview, and playlist creation as MCP tools, install `uv` and run the MCP server from this repository:

```sh
uv sync --extra mcp
```

The included `.mcp.json` starts the local stdio server with `uv run --extra mcp ug-spotify-mcp`. Configure the Spotify developer app environment variables from above in the MCP client's environment. Tools are named `convert_ultimate_guitar_pdf`, `preview_spotify_matches`, and `create_spotify_playlist`. Preview is read-only; playlist creation requires the preview ID and `confirm_create=true`, and always creates a new private playlist.

Claude Code users can use the included `.claude/skills/ug-spotify-playlist/SKILL.md` workflow. It requires reviewing the match report and user approval before playlist creation.

## Convert PDF export to CSV

```sh
ug-tabs-pdf-to-csv path/to/ultimate-guitar-my-tabs.pdf
```

By default this creates a sibling CSV with the same base filename. To choose another path:

```sh
ug-tabs-pdf-to-csv path/to/ultimate-guitar-my-tabs.pdf --output favorites.csv
```

The converter is intended for text-based PDFs saved from the Ultimate Guitar My Tabs page. It preserves source order and outputs `title,artist,saved_date,tab_type`. If the PDF is scanned or its table layout differs, conversion fails instead of silently claiming success; use OCR or correct the CSV manually in that case.

## Preview and review

Ultimate Guitar exports with `title` and `artist` columns are supported. Songs are processed in CSV order. When the artist column contains a generic category such as “Misc Soundtrack,” it is ignored; a title shaped like `Artist - Song` is split when appropriate.

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
