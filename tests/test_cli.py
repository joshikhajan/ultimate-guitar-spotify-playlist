import csv

from ug_spotify.cli import (
    Match,
    Song,
    create_playlist,
    match_all,
    match_song,
    parse_song,
    read_songs,
    write_report,
)


class FakeSpotify:
    def __init__(self, results):
        self.results = results
        self.added = []

    def search(self, q, type, limit):
        title = q.split('track:"', 1)[1].split('"', 1)[0]
        return {"tracks": {"items": self.results.get(title, [])}}

    def current_user(self):
        return {"id": "user"}

    def user_playlist_create(self, **kwargs):
        self.playlist_args = kwargs
        return {"id": "playlist", "external_urls": {"spotify": "https://open.spotify.com/playlist/test"}}

    def playlist_add_items(self, playlist_id, ids):
        self.added.extend(ids)


def track(track_id, name, artist="Singer"):
    return {
        "id": track_id,
        "name": name,
        "artists": [{"name": artist}],
        "external_urls": {"spotify": f"https://open.spotify.com/track/{track_id}"},
    }


def test_read_and_parse_ug_csv_in_source_order(tmp_path):
    source = tmp_path / "favorites.csv"
    source.write_text(
        "title,artist,saved_date,tab_type\n"
        '"Artist Name - First Song",Misc Soundtrack,today,Chords\n'
        "Second Song,Actual Singer,today,Chords\n",
        encoding="utf-8",
    )
    songs = read_songs(source)
    assert [song.title for song in songs] == ["First Song", "Second Song"]
    assert [song.artist for song in songs] == ["Artist Name", "Actual Singer"]


def test_exact_and_artist_match_and_unmatched():
    sp = FakeSpotify(
        {
            "Known": [track("one", "Known", "Preferred Artist"), track("two", "Known", "Other Artist")],
            "Missing": [],
        }
    )
    assert match_song(sp, Song(2, "Known", "Preferred Artist")).track["id"] == "one"
    assert match_song(sp, Song(3, "Missing")).status == "unmatched"


def test_ambiguous_song_is_not_guessed():
    sp = FakeSpotify({"Song": [track("one", "Song", "Singer A"), track("two", "Song", "Singer B")]})
    result = match_song(sp, Song(2, "Song"))
    assert result.status == "ambiguous"
    assert result.track is None


def test_duplicate_spotify_recording_is_skipped():
    repeated = track("same", "Song")
    sp = FakeSpotify({"Song": [repeated]})
    matches = match_all(sp, [Song(2, "Song"), Song(3, "Song")])
    assert [match.status for match in matches] == ["matched", "duplicate"]


def test_playlist_created_private_in_order_and_chunked():
    sp = FakeSpotify({})
    matches = [Match(Song(i, str(i)), "matched", track(str(i), str(i))) for i in range(1, 202)]
    url = create_playlist(sp, "Test playlist", matches)
    assert url.endswith("/test")
    assert sp.playlist_args["public"] is False
    assert len(sp.added) == 201
    assert sp.added[:2] == ["1", "2"]
    assert sp.added[-1] == "201"


def test_report_contains_unmatched_and_review_details(tmp_path):
    report = tmp_path / "report.csv"
    matches = [Match(Song(2, "Unknown", "Artist"), "unmatched", note="No results")]
    write_report(matches, report)
    with report.open(encoding="utf-8") as source:
        row = next(csv.DictReader(source))
    assert row["source_title"] == "Unknown"
    assert row["status"] == "unmatched"
    assert row["note"] == "No results"
