from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from spotify_recommender import account_ui, spotify
from spotify_recommender.spotify import SpotifyClient, SpotifyError


@pytest.fixture
def app(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SPOTIFY_DATASET", str(root / "data/sample/spotify_tracks_sample.csv"))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(tmp_path / "library.db"))
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    app.button(key="demo_taste").click().run()
    app.button(key="build_playlist").click().run()
    app.text_input(key="playlist_name").set_value("Evening discovery").run()
    return app


@pytest.mark.parametrize("outcome", ["complete", "unknown"])
def test_export_requires_confirmation_and_remembers_outcome(app, monkeypatch, outcome):
    calls = []

    def request(request):
        calls.append(request)
        if len(calls) == 1:
            return {"id": "p" * 22}
        if outcome == "unknown":
            raise SpotifyError("Could not reach Spotify.")
        return {"snapshot_id": "saved"}

    monkeypatch.setattr(spotify, "request_json", request)
    app.session_state["spotify_client"] = SpotifyClient("a" * 32, {
        "access_token": "test", "scope": "playlist-modify-private", "expires_in": 3600,
    })
    app.run()
    assert not calls
    assert app.button(key="save_spotify").disabled
    app.checkbox(key="confirm_spotify_export").check().run()
    app.button(key="save_spotify").click().run()
    assert len(calls) == 2
    assert app.button(key="save_spotify").disabled
    app.run()
    assert len(calls) == 2
    assert any("Open playlist" in item.proto.label for item in app.get("link_button"))
    if outcome == "complete":
        assert any("Saved privately" in item.value for item in app.success)
    else:
        assert any("Check Spotify" in item.value for item in app.warning)
    assert not app.exception


def test_write_permission_requires_explicit_opt_in(app, monkeypatch):
    requested = []

    class Attempt:
        url = "https://accounts.spotify.com/authorize"

        def __init__(self, client_id, *, allow_playlist_export=False):
            requested.append(allow_playlist_export)

        def finish(self):
            return SpotifyClient("a" * 32, {
                "access_token": "test", "scope": "playlist-modify-private",
            })

        def close(self):
            pass

    monkeypatch.setattr(account_ui, "LoginAttempt", Attempt)
    app.session_state["spotify_client"] = SpotifyClient("a" * 32, {"access_token": "test"})
    app.run()
    app.button(key="enable_spotify_export").click().run()
    assert requested == [True]
    app.button(key="finish_spotify").click().run()
    assert app.session_state["spotify_client"].can_export
    assert len(app.session_state["playlist"]) > 0
    assert not app.exception


def test_changing_name_or_tracks_resets_confirmation(app):
    app.session_state["spotify_client"] = SpotifyClient("a" * 32, {
        "access_token": "test", "scope": "playlist-modify-private",
    })
    app.run()
    app.checkbox(key="confirm_spotify_export").check().run()
    assert not app.button(key="save_spotify").disabled
    app.text_input(key="playlist_name").set_value("A different playlist").run()
    assert not app.checkbox(key="confirm_spotify_export").value
    app.checkbox(key="confirm_spotify_export").check().run()
    track_id = app.session_state["playlist"].iloc[0]["track_id"]
    app.button(key=f"hide-{track_id}").click().run()
    assert not app.checkbox(key="confirm_spotify_export").value
    assert not app.exception


def test_expired_session_and_name_bounds_do_not_write(app, monkeypatch):
    monkeypatch.setattr(spotify, "request_json", lambda _: pytest.fail("Unexpected API call"))
    app.session_state["spotify_client"] = SpotifyClient("a" * 32, {
        "access_token": "test", "scope": "playlist-modify-private", "expires_in": 1,
    })
    app.run()
    app.checkbox(key="confirm_spotify_export").check().run()
    app.button(key="save_spotify").click().run()
    assert any("expired" in item.value for item in app.error)
    app.text_input(key="playlist_name").set_value("x" * 101).run()
    assert len(app.text_input(key="playlist_name").value) == 100
    assert app.button(key="save_spotify").disabled
    assert not app.exception
