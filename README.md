# Ultimate Guitar → Spotify playlist

A small command-line tool that reads an Ultimate Guitar favorites CSV export, searches Spotify for likely recordings, and creates a private, source-ordered playlist. It does not access Ultimate Guitar or scrape a logged-in browser session: provide a CSV export you obtained yourself.

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

## Preview and review

Ultimate Guitar exports with `title` and `artist` columns are supported. Songs are processed in CSV order. When the artist column contains a generic category such as “Misc Soundtrack,” it is ignored; a title shaped like `Artist - Song` is split when appropriate.

```sh
ug-spotify-playlist path/to/ultimate-guitar-favorites.csv
```

The default is preview-only. It prints counts and writes `matches.csv` for review. High-confidence matches are included; ambiguous or unmatched entries are not guessed. Identical Spotify track IDs are only added once, keeping the first source occurrence.

Inspect the report, correct the source CSV if needed, and rerun with the explicit `--apply` flag to create a new **private** playlist:

```sh
ug-spotify-playlist path/to/ultimate-guitar-favorites.csv \
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
