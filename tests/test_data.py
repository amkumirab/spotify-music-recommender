from __future__ import annotations

import pandas as pd
import pytest

from spotify_recommender.data import display_label, find_tracks, load_tracks


def test_load_tracks_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        load_tracks(tmp_path / "missing.csv")


def test_load_tracks_rejects_missing_columns(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"track_id": ["one"]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="missing required columns"):
        load_tracks(path)


def test_find_tracks_matches_artist(sample_tracks):
    results = find_tracks(sample_tracks, "artist b")

    assert results.iloc[0]["track_id"] == "b"


def test_load_tracks_cleans_numeric_values_and_duplicate_ids(tmp_path, sample_tracks):
    duplicate = sample_tracks.iloc[[0]].copy()
    duplicate["popularity"] = 1
    dirty = pd.concat([sample_tracks, duplicate], ignore_index=True)
    dirty["energy"] = dirty["energy"].astype("object")
    dirty.loc[1, "energy"] = "not-a-number"
    path = tmp_path / "tracks.csv"
    dirty.to_csv(path, index=False)

    result = load_tracks(path)

    assert len(result) == 3
    assert result["track_id"].is_unique
    assert result["energy"].notna().all()
    assert result.loc[result["track_id"].eq("a"), "popularity"].item() == 50


def test_find_tracks_handles_empty_query_and_title(sample_tracks):
    popular = find_tracks(sample_tracks, "", limit=2)
    title_match = find_tracks(sample_tracks, "quiet piano")

    assert list(popular["track_id"]) == ["b", "a"]
    assert title_match.iloc[0]["track_id"] == "c"


def test_display_label_contains_track_artist_and_genre(sample_tracks):
    label = display_label(sample_tracks.iloc[0])

    assert label == "Bright Morning — Artist A · pop"
