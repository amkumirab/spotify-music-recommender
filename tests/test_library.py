import pandas as pd
import pytest

from spotify_recommender.library import PlaylistLibrary
from spotify_recommender.model import ContentBasedRecommender


def test_library_survives_restart_and_preserves_order(tmp_path, sample_tracks):
    path = tmp_path / "nested" / "library.db"
    result = ContentBasedRecommender().fit(sample_tracks).recommend("a", 2)
    library = PlaylistLibrary(path)
    playlist_id = library.save("Evening's mix", result, {"seeds": ["a"]})
    restarted = PlaylistLibrary(path)
    saved = restarted.load(playlist_id)
    assert saved["name"] == "Evening's mix"
    assert saved["settings"] == {"seeds": ["a"]}
    assert saved["tracks"]["track_id"].tolist() == result["track_id"].tolist()
    assert restarted.list_playlists()[0]["track_count"] == 2
    restarted.delete(playlist_id)
    assert restarted.list_playlists() == []
    with pytest.raises(KeyError):
        restarted.load(playlist_id)


def test_library_rejects_invalid_snapshots(tmp_path):
    library = PlaylistLibrary(tmp_path / "library.db")
    with pytest.raises(ValueError):
        library.save(" ", pd.DataFrame(), {})
    with pytest.raises(ValueError):
        library.save("Empty", pd.DataFrame(), {})
