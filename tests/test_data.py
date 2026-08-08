from __future__ import annotations

import pandas as pd
import pytest

from spotify_recommender.data import find_tracks, load_tracks


def test_load_tracks_rejects_missing_columns(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"track_id": ["one"]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="missing required columns"):
        load_tracks(path)


def test_find_tracks_matches_artist(sample_tracks):
    results = find_tracks(sample_tracks, "artist b")

    assert results.iloc[0]["track_id"] == "b"
