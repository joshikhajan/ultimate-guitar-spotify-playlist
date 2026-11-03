"""MCP tools for the Ultimate Guitar to Spotify workflow."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .cli import _spotify_client, create_playlist, match_all, read_songs, write_report
from .pdf_to_csv import convert_pdf


mcp = FastMCP("ultimate-guitar-spotify")
_previews: dict[str, tuple[Any, list[Any]]] = {}


@mcp.tool()
def convert_ultimate_guitar_pdf(pdf_path: str, csv_path: str | None = None) -> dict[str, Any]:
    """Convert a text-based Ultimate Guitar My Tabs PDF export to CSV on the local machine."""
    source = Path(pdf_path).expanduser()
    destination = Path(csv_path).expanduser() if csv_path else source.with_suffix(".csv")
    count = convert_pdf(source, destination)
    return {"csv_path": str(destination.resolve()), "songs_converted": count}


@mcp.tool()
def preview_spotify_matches(csv_path: str, report_path: str = "matches.csv") -> dict[str, Any]:
    """Search Spotify and save a local review CSV; this does not create or modify any playlist."""
    songs = read_songs(Path(csv_path).expanduser())
    spotify = _spotify_client()
    matches = match_all(spotify, songs)
    report = Path(report_path).expanduser()
    write_report(matches, report)
    preview_id = secrets.token_urlsafe(24)
    _previews[preview_id] = (spotify, matches)

    counts = {
        status: sum(match.status == status for match in matches)
        for status in ("matched", "ambiguous", "unmatched", "duplicate")
    }
    return {
        "preview_id": preview_id,
        "counts": counts,
        "report_path": str(report.resolve()),
        "matched_tracks": [
            {
                "source_row": match.song.row,
                "title": match.song.title,
                "artist": ", ".join(
                    artist.get("name", "")
                    for artist in (match.track or {}).get("artists", [])
                ),
                "spotify_url": (match.track or {}).get("external_urls", {}).get("spotify", ""),
            }
            for match in matches
            if match.status == "matched" and match.track
        ],
        "ambiguous_or_unmatched": [
            {
                "source_row": match.song.row,
                "title": match.song.title,
                "status": match.status,
                "note": match.note,
            }
            for match in matches
            if match.status in {"ambiguous", "unmatched"}
        ],
        "next_step": "Review the report and matches. Only then call create_spotify_playlist with this preview_id and confirm_create=true.",
    }


@mcp.tool()
def create_spotify_playlist(
    preview_id: str,
    playlist_name: str,
    confirm_create: bool,
) -> dict[str, Any]:
    """Create a new private playlist from a reviewed preview; never edits an existing playlist."""
    if not confirm_create:
        raise ValueError("Set confirm_create=true only after the user approves creating this new playlist.")
    preview = _previews.pop(preview_id, None)
    if preview is None:
        raise ValueError("Preview not found or already used. Run preview_spotify_matches again.")
    spotify, matches = preview
    url = create_playlist(spotify, playlist_name, matches, public=False)
    return {
        "playlist_name": playlist_name,
        "playlist_url": url,
        "tracks_added": sum(match.status == "matched" for match in matches),
        "visibility": "private",
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
