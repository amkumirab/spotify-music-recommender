from pathlib import Path

from streamlit.testing.v1 import AppTest

from spotify_recommender.library import PlaylistLibrary


def test_feedback_can_be_applied_paused_and_undone_after_restart(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    library_path = tmp_path / "library.db"
    monkeypatch.setenv("SPOTIFY_DATASET", str(root / "data/sample/spotify_tracks_sample.csv"))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(library_path))
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    app.button(key="demo_taste").click().run()
    app.button(key="build_playlist").click().run()
    original = app.session_state["playlist"].copy()
    track_id = original.iloc[0]["track_id"]
    app.button(key=f"feedback-less-{track_id}").click().run()
    assert PlaylistLibrary(library_path).list_feedback() == {track_id: -1}
    assert app.session_state["playlist"].equals(original)
    assert any("Build again" in item.value for item in app.info)
    app.button(key="build_playlist").click().run()
    assert app.session_state["playlist"]["track_id"].tolist() != original["track_id"].tolist()

    app.checkbox(key="use_feedback").uncheck().run()
    app.button(key="build_playlist").click().run()
    assert app.session_state["playlist"].equals(original)
    app.button(key=f"feedback-more-{original.iloc[1]['track_id']}").click().run()
    assert len(PlaylistLibrary(library_path).list_feedback()) == 2
    assert not app.exception

    restarted = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    restarted.selectbox(key="feedback_track").set_value(track_id).run()
    restarted.button(key="undo_saved_feedback").click().run()
    assert PlaylistLibrary(library_path).list_feedback() == {original.iloc[1]["track_id"]: 1}
    assert not restarted.exception


def test_unavailable_feedback_storage_does_not_prevent_offline_discovery(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SPOTIFY_DATASET", str(root / "data/sample/spotify_tracks_sample.csv"))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(tmp_path))
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    app.button(key="demo_taste").click().run()
    app.button(key="build_playlist").click().run()
    assert len(app.session_state["playlist"]) == 10
    assert any("Local storage is unavailable" in warning.value for warning in app.warning)
    assert not app.exception
