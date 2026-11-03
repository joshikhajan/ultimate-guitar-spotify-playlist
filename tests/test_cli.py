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
from ug_spotify.pdf_to_csv import convert_pdf


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


def test_convert_pdf_export_to_csv(tmp_path, monkeypatch):
    class FakePage:
        def extract_words(self):
            return [
                {"x0": 160, "top": 100, "text": "ARTIST"},
                {"x0": 320, "top": 100, "text": "SONG"},
                {"x0": 620, "top": 100, "text": "DATE"},
                {"x0": 710, "top": 100, "text": "TYPE"},
                {"x0": 160, "top": 120, "text": "Artist"},
                {"x0": 190, "top": 120, "text": "One"},
                {"x0": 320, "top": 120, "text": "First"},
                {"x0": 350, "top": 120, "text": "Song"},
                {"x0": 620, "top": 120, "text": "4"},
                {"x0": 630, "top": 120, "text": "days"},
                {"x0": 660, "top": 120, "text": "ago"},
                {"x0": 710, "top": 120, "text": "Chords"},
                {"x0": 320, "top": 140, "text": "Second"},
                {"x0": 360, "top": 140, "text": "Song"},
                {"x0": 620, "top": 140, "text": "3"},
                {"x0": 630, "top": 140, "text": "days"},
                {"x0": 660, "top": 140, "text": "ago"},
                {"x0": 710, "top": 140, "text": "Chords"},
            ]

    class FakePDF:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakePdfPlumber:
        @staticmethod
        def open(path):
            return FakePDF()

    monkeypatch.setattr("ug_spotify.pdf_to_csv.pdfplumber", FakePdfPlumber)
    source = tmp_path / "source.pdf"
    source.touch()
    destination = tmp_path / "songs.csv"
    assert convert_pdf(source, destination) == 2
    with destination.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0] == {
        "title": "First Song",
        "artist": "Artist One",
        "saved_date": "4 days ago",
        "tab_type": "Chords",
    }
    assert rows[1]["title"] == "Second Song"
    assert rows[1]["artist"] == ""
