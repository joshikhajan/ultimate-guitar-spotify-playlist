from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable


GENERIC_ARTISTS = {
    "misc soundtrack",
    "misc unsigned bands",
    "misc television",
    "misc soundtracks",
    "misc",
    "unknown",
}


@dataclass(frozen=True)
class Song:
    row: int
    title: str
    artist: str = ""


@dataclass(frozen=True)
class Match:
    song: Song
    status: str
    track: dict[str, Any] | None = None
    note: str = ""


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def parse_song(title: str, artist: str = "", row: int = 0) -> Song:
    title = title.strip()
    artist = artist.strip()
    # UG exports sometimes put the performer and song together in the title.
    # Split only when the separate artist column is empty or a generic category.
    if " - " in title and normalize(artist) in {"", *(normalize(x) for x in GENERIC_ARTISTS)}:
        left, right = (part.strip() for part in title.split(" - ", 1))
        if left and right:
            title, artist = right, left
    if normalize(artist) in {normalize(x) for x in GENERIC_ARTISTS}:
        artist = ""
    return Song(row=row, title=title, artist=artist)


def read_songs(path: Path) -> list[Song]:
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "title" not in {name.strip().lower() for name in reader.fieldnames}:
            raise ValueError("CSV must have a 'title' column.")
        title_field = next(name for name in reader.fieldnames if name.strip().lower() == "title")
        artist_field = next(
            (name for name in reader.fieldnames if name.strip().lower() == "artist"), None
        )
        songs = []
        for row_number, row in enumerate(reader, start=2):
            title = (row.get(title_field) or "").strip()
            if not title:
                continue
            artist = (row.get(artist_field) or "").strip() if artist_field else ""
            songs.append(parse_song(title, artist, row_number))
    if not songs:
        raise ValueError("No titled songs were found in the CSV.")
    return songs


def _track_artists(track: dict[str, Any]) -> list[str]:
    return [artist.get("name", "") for artist in track.get("artists", [])]


def _title_score(song_title: str, track_title: str) -> float:
    return SequenceMatcher(None, normalize(song_title), normalize(track_title)).ratio()


def _artist_matches(song_artist: str, track: dict[str, Any]) -> bool:
    expected = normalize(song_artist)
    if not expected:
        return False
    return any(
        expected == normalize(name)
        or expected in normalize(name)
        or normalize(name) in expected
        for name in _track_artists(track)
    )


def match_song(sp: Any, song: Song) -> Match:
    query = f'track:"{song.title}"'
    if song.artist:
        query += f' artist:"{song.artist}"'
    response = sp.search(q=query, type="track", limit=10)
    tracks = response.get("tracks", {}).get("items", [])
    if not tracks:
        return Match(song, "unmatched", note="No Spotify search results.")

    scored = sorted(
        ((_title_score(song.title, track.get("name", "")), track) for track in tracks),
        key=lambda item: item[0],
        reverse=True,
    )
    best_score = scored[0][0]
    close = [track for score, track in scored if score >= max(0.90, best_score - 0.02)]
    if song.artist:
        artist_matches = [track for track in close if _artist_matches(song.artist, track)]
        if len(artist_matches) == 1 and best_score >= 0.78:
            return Match(song, "matched", artist_matches[0], "title and artist matched")
        if len(artist_matches) > 1:
            return Match(song, "ambiguous", note="Several close title and artist matches.")

    exact = [track for track in close if normalize(track.get("name", "")) == normalize(song.title)]
    if len(exact) == 1:
        return Match(song, "matched", exact[0], "exact normalized title")
    if len(exact) > 1:
        return Match(song, "ambiguous", note="Several Spotify recordings have this title.")
    if best_score >= 0.94 and len(close) == 1:
        return Match(song, "matched", scored[0][1], "high-confidence title match")
    return Match(song, "ambiguous", note="Review the possible Spotify matches manually.")


def match_all(sp: Any, songs: Iterable[Song]) -> list[Match]:
    results: list[Match] = []
    seen_track_ids: set[str] = set()
    for song in songs:
        match = match_song(sp, song)
        if match.track:
            track_id = match.track.get("id")
            if not track_id:
                match = Match(song, "unmatched", note="Spotify result has no track ID.")
            elif track_id in seen_track_ids:
                match = Match(song, "duplicate", match.track, "same Spotify recording already matched")
            else:
                seen_track_ids.add(track_id)
        results.append(match)
    return results


def write_report(matches: list[Match], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.writer(destination)
        writer.writerow(["source_row", "status", "source_title", "source_artist", "spotify_track", "spotify_artists", "spotify_url", "note"])
        for match in matches:
            track = match.track or {}
            writer.writerow(
                [
                    match.song.row,
                    match.status,
                    match.song.title,
                    match.song.artist,
                    track.get("name", ""),
                    ", ".join(_track_artists(track)),
                    track.get("external_urls", {}).get("spotify", ""),
                    match.note,
                ]
            )


def create_playlist(sp: Any, name: str, matches: list[Match], public: bool = False) -> str:
    user_id = sp.current_user()["id"]
    playlist = sp.user_playlist_create(
        user=user_id,
        name=name,
        public=public,
        description="Created from an Ultimate Guitar favorites CSV export.",
    )
    track_ids = [match.track["id"] for match in matches if match.status == "matched" and match.track]
    for start in range(0, len(track_ids), 100):
        sp.playlist_add_items(playlist["id"], track_ids[start : start + 100])
    return playlist.get("external_urls", {}).get("spotify", playlist["id"])


def _spotify_client() -> Any:
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError as error:
        raise RuntimeError("Install dependencies with: python -m pip install .") from error

    required = ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(
            "Set up a Spotify developer app and configure: " + ", ".join(missing)
        )
    token_cache = Path.home() / ".cache" / "ug-spotify-playlist" / "token.json"
    token_cache.parent.mkdir(parents=True, exist_ok=True)
    auth = SpotifyOAuth(
        scope="playlist-modify-private playlist-modify-public",
        cache_path=str(token_cache),
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview Spotify matches for an Ultimate Guitar favorites CSV export."
    )
    parser.add_argument("csv_file", type=Path, help="CSV file with title and optional artist columns")
    parser.add_argument("--playlist", default="Ultimate Guitar", help="Playlist name (default: Ultimate Guitar)")
    parser.add_argument("--report", type=Path, default=Path("matches.csv"), help="Write a review CSV (default: matches.csv)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create a new Spotify playlist from high-confidence unique matches; default is preview only.",
    )
    parser.add_argument("--public", action="store_true", help="Make the new playlist public (private by default).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        songs = read_songs(args.csv_file)
        sp = _spotify_client()
        matches = match_all(sp, songs)
        write_report(matches, args.report)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    counts = {status: sum(match.status == status for match in matches) for status in ("matched", "ambiguous", "unmatched", "duplicate")}
    print(
        f"Source songs: {len(songs)} | matched: {counts['matched']} | "
        f"ambiguous: {counts['ambiguous']} | unmatched: {counts['unmatched']} | "
        f"duplicate recordings skipped: {counts['duplicate']}"
    )
    print(f"Review report: {args.report}")
    if not args.apply:
        print("Preview only; inspect the report, then rerun with --apply to create a playlist.")
        return 0

    if not counts["matched"]:
        print("No confident matches to add; playlist was not created.", file=sys.stderr)
        return 2
    try:
        url = create_playlist(sp, args.playlist, matches, public=args.public)
    except Exception as error:
        print(f"Spotify could not create the playlist: {error}", file=sys.stderr)
        return 2
    print(f"Created playlist with {counts['matched']} tracks: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
