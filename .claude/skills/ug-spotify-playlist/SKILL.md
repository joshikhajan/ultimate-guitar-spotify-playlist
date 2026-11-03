---
name: ug-spotify-playlist
description: Convert an Ultimate Guitar My Tabs PDF export or CSV into a reviewed, ordered Spotify playlist using the repository CLI or MCP tools.
---

# Ultimate Guitar to Spotify

Use the local tools in this repository to help the user create a Spotify playlist from their own Ultimate Guitar export.

## Workflow

1. If given a PDF export, use `convert_ultimate_guitar_pdf` (MCP) or `ug-tabs-pdf-to-csv` (CLI) to convert it. Do not upload the PDF or resulting CSV to GitHub or another service.
2. Run `preview_spotify_matches` or the CLI without `--apply`. Explain the match counts and the location of the local report. Ambiguous and unmatched entries are intentionally left out.
3. Ask the user to review/approve playlist creation before making changes to Spotify. Do not infer consent from a request to preview.
4. Only after approval, call `create_spotify_playlist` with the returned `preview_id`, chosen playlist name, and `confirm_create: true`, or rerun the CLI with `--apply`. This creates a new private playlist; it does not edit an existing playlist.
5. Report the resulting playlist link and the number of tracks added.

## Safety and privacy

- Spotify matching sends song titles and any available artists to Spotify search.
- Never print, commit, or share Spotify client secrets, OAuth tokens, token-cache files, or the user's source export.
- Keep playlist creation private unless the user explicitly requests a public playlist.
- Preserve CSV order and deduplicate by Spotify track ID. Never guess uncertain recordings.
- The MCP `preview_id` is process-local and single-use; if it is unavailable or expired, rerun the preview.
