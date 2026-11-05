from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_playlist_persists_and_can_be_hidden_saved_and_reopened(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SPOTIFY_DATASET", str(root / "data/sample/spotify_tracks_sample.csv"))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(tmp_path / "library.db"))
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    assert not app.exception
    app.button(key="add_seed").click().run()
    app.button(key="build_playlist").click().run()
    assert not app.exception
    original = app.session_state["playlist"].copy()
    assert len(original) == 10
    app.text_input(key="search_query").set_value("Coldplay").run()
    assert app.session_state["playlist"].equals(original)
    app.button(key=f"hide-{original.iloc[0]['track_id']}").click().run()
    assert len(app.session_state["playlist"]) == 9
    assert original.iloc[0]["track_id"] in app.session_state["excluded_track_ids"]
    app.text_input(key="playlist_name").set_value("Night drive").run()
    app.button(key="save_playlist").click().run()
    assert not app.exception
    app.button(key="build_playlist").click().run()
    assert original.iloc[0]["track_id"] not in app.session_state["playlist"]["track_id"].tolist()
    app.slider[0].set_value(5).run()
    assert any("Build again" in item.value for item in app.info)
    app.button(key="open_saved").click().run()
    assert len(app.session_state["playlist"]) == 9
    assert not app.exception
    app.button(key="restore_hidden").click().run()
    assert app.session_state["excluded_track_ids"] == []


def test_audio_filters_empty_state_and_name_validation(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SPOTIFY_DATASET", str(root / "data/sample/spotify_tracks_sample.csv"))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(tmp_path / "library.db"))
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    app.button(key="add_seed").click().run()
    app.button(key="build_playlist").click().run()
    app.button(key="save_playlist").click().run()
    assert any("name must contain" in item.value for item in app.warning)
    app.checkbox(key="use_audio_filters").check().run()
    tempo = next(slider for slider in app.slider if slider.label == "Tempo range (BPM)")
    tempo.set_value((395, 400)).run()
    app.button(key="build_playlist").click().run()
    assert app.session_state["playlist"].empty
    assert any("No tracks remain" in item.value for item in app.warning)
    assert not app.exception


def test_demo_discovery_excludes_all_imported_tracks(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SPOTIFY_DATASET", str(root / "data/sample/spotify_tracks_sample.csv"))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(tmp_path / "library.db"))
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    app.button(key="demo_taste").click().run()
    report = app.session_state["library_report"]
    assert report["matched"] > 0
    app.button(key="build_playlist").click().run()
    assert not app.exception
    assert len(app.session_state["playlist"]) == 10
    assert set(app.session_state["playlist"]["track_id"]).isdisjoint(report["excluded_ids"])
    assert "not a connected account" in app.session_state["library_source"]
    app.button(key="clear_taste").click().run()
    assert "library_report" not in app.session_state


def test_connection_rejects_invalid_client_id(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("SPOTIFY_DATASET", str(root / "data/sample/spotify_tracks_sample.csv"))
    monkeypatch.setenv("SPOTIFY_LIBRARY", str(tmp_path / "library.db"))
    app = AppTest.from_file(str(root / "app.py"), default_timeout=30).run()
    app.text_input(key="spotify_client_id").set_value("invalid").run()
    app.button(key="start_spotify").click().run()
    assert any("32-character" in error.value for error in app.error)
    assert not app.exception
