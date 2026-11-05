from pathlib import Path

from streamlit.testing.v1 import AppTest

from spotify_recommender.data import load_tracks


def test_sync_and_disconnect_flow(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    dataset = root / "data/sample/spotify_tracks_sample.csv"
    monkeypatch.setenv("SPOTIFY_DATASET", str(dataset))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(tmp_path / "library.db"))
    likes = load_tracks(dataset).head(8).to_dict("records")

    class TestClient:
        def liked_songs(self):
            return likes

    app = AppTest.from_file(str(root / "app.py"), default_timeout=30)
    app.session_state["spotify_client"] = TestClient()
    app.run()
    app.button(key="sync_likes").click().run()
    assert app.session_state["library_source"] == "Spotify Liked Songs"
    assert app.session_state["library_report"]["matched"] == 8
    app.button(key="build_playlist").click().run()
    assert not app.exception
    app.button(key="disconnect_spotify").click().run()
    assert "spotify_client" not in app.session_state
    assert "library_report" not in app.session_state
    assert app.session_state["playlist"] is None
    assert not app.exception


def test_connection_completion_and_sync_errors(tmp_path, monkeypatch):
    from spotify_recommender import account_ui
    from spotify_recommender.spotify import SpotifyError

    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SPOTIFY_DATASET", str(root / "data/sample/spotify_tracks_sample.csv"))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(tmp_path / "library.db"))

    class FailingClient:
        def liked_songs(self):
            raise SpotifyError("Spotify rate limit reached. Wait and sync again later.")

    class Attempt:
        url = "https://accounts.spotify.com/authorize"

        def __init__(self, client_id):
            pass

        def finish(self):
            return FailingClient()

        def close(self):
            pass

    monkeypatch.setattr(account_ui, "LoginAttempt", Attempt)
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    app.text_input(key="spotify_client_id").set_value("a" * 32).run()
    app.button(key="start_spotify").click().run()
    app.button(key="finish_spotify").click().run()
    assert "spotify_login" not in app.session_state
    assert "spotify_client" in app.session_state
    app.button(key="sync_likes").click().run()
    assert any("rate limit" in error.value for error in app.error)
    assert not app.exception


def test_pasted_unknown_ids_report_coverage(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    dataset = root / "data/sample/spotify_tracks_sample.csv"
    monkeypatch.setenv("SPOTIFY_DATASET", str(dataset))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(tmp_path / "library.db"))
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    app.text_area(key="import_links").set_value("spotify:track:" + "0" * 22).run()
    app.button(key="import_taste").click().run()
    assert app.session_state["library_report"]["unmatched"] == 1
    assert app.button(key="build_playlist").disabled
    assert not app.exception
