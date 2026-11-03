import csv

import pytest

from ug_spotify import mcp_server


class FakeSpotify:
    def __init__(self):
        self.created = []
        self.added = []

    def search(self, q, type, limit):
        assert type == "track"
        assert limit == 10
        return {
            "tracks": {
                "items": [
                    {
                        "id": "track-1",
                        "name": "First Song",
                        "artists": [{"name": "Artist One"}],
                        "external_urls": {"spotify": "https://open.spotify.com/track/track-1"},
                    }
                ]
            }
        }

    def current_user(self):
        return {"id": "test-user"}

    def user_playlist_create(self, **kwargs):
        self.created.append(kwargs)
        return {
            "id": "new-playlist",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/new-playlist"},
        }

    def playlist_add_items(self, playlist_id, ids):
        self.added.extend(ids)


def test_mcp_registers_expected_tools():
    tools = mcp_server.mcp._tool_manager.list_tools()
    assert {tool.name for tool in tools} == {
        "convert_ultimate_guitar_pdf",
        "preview_spotify_matches",
        "create_spotify_playlist",
    }


def test_mcp_preview_is_read_only_until_confirmed(tmp_path, monkeypatch):
    source = tmp_path / "favorites.csv"
    with source.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["title", "artist", "saved_date", "tab_type"])
        writer.writerow(["First Song", "Artist One", "today", "Chords"])

    spotify = FakeSpotify()
    monkeypatch.setattr(mcp_server, "_spotify_client", lambda: spotify)
    mcp_server._previews.clear()

    preview = mcp_server.preview_spotify_matches(str(source), str(tmp_path / "review.csv"))
    assert preview["counts"] == {"matched": 1, "ambiguous": 0, "unmatched": 0, "duplicate": 0}
    assert preview["matched_tracks"][0]["spotify_url"].endswith("track-1")
    assert (tmp_path / "review.csv").is_file()
    assert spotify.created == []
    assert spotify.added == []

    with pytest.raises(ValueError, match="confirm_create=true"):
        mcp_server.create_spotify_playlist(preview["preview_id"], "Test", False)
    assert preview["preview_id"] in mcp_server._previews
    assert spotify.created == []

    result = mcp_server.create_spotify_playlist(preview["preview_id"], "Test", True)
    assert result["visibility"] == "private"
    assert result["tracks_added"] == 1
    assert spotify.created[0]["public"] is False
    assert spotify.added == ["track-1"]

    with pytest.raises(ValueError, match="Preview not found"):
        mcp_server.create_spotify_playlist(preview["preview_id"], "Test", True)
