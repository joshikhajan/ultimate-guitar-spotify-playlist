---
name: spotify-playlist
description: Create a reviewed, ordered Spotify playlist from a song-list CSV from any source, or convert an Ultimate Guitar My Tabs PDF first.
---

# Create Spotify playlists from song lists

Use the local tools in this plugin to create a Spotify playlist from a CSV song list. This works with exports from any source when they have a title/track/song column and optionally an artist/performer/band column. Ultimate Guitar My Tabs PDF exports can first be converted to CSV.

## Workflow

1. If given an Ultimate Guitar PDF export, use `convert_ultimate_guitar_pdf` (MCP) or `ug-tabs-pdf-to-csv` (CLI) to convert it. For other sources, use their CSV directly. Do not upload the source export to GitHub or another service.
2. Run `preview_spotify_matches` or the CLI without `--apply`. Explain the match counts and the location of the local report. Ambiguous and unmatched entries are intentionally left out.
3. Ask the user to review/approve playlist creation before making changes to Spotify. Do not infer consent from a request to preview.
4. Only after approval, call `create_spotify_playlist` with the returned `preview_id`, chosen playlist name, and `confirm_create: true`, or rerun the CLI with `--apply`. This creates a new private playlist; it does not edit an existing playlist.
5. Report the resulting playlist link and the number of tracks added.

## Safety and privacy

- Spotify matching sends song titles and any available artists to Spotify search.
- Never print, commit, or share Spotify client secrets, OAuth tokens, token-cache files, or the user's source export.
- Keep playlist creation private unless the user explicitly requests a public playlist.
- Accept common CSV headers: `title`, `track`, or `song`, with optional `artist`, `performer`, or `band`. Preserve CSV order and deduplicate by Spotify track ID. Never guess uncertain recordings.
- The MCP `preview_id` is process-local and single-use; if it is unavailable or expired, rerun the preview.
