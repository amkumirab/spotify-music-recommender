from __future__ import annotations

import pandas as pd
import pytest

from spotify_recommender.model import ContentBasedRecommender


def test_recommender_returns_nearest_track(sample_tracks):
    model = ContentBasedRecommender().fit(sample_tracks)

    result = model.recommend("a", n_recommendations=1, popularity_bias=0)

    assert result.iloc[0]["track_id"] == "b"
    assert 0 <= result.iloc[0]["similarity"] <= 1
    assert result.iloc[0]["reason"].startswith("Similar")


def test_recommender_rejects_unknown_track(sample_tracks):
    model = ContentBasedRecommender().fit(sample_tracks)

    with pytest.raises(KeyError, match="Unknown track_id"):
        model.recommend("missing")


def test_recommender_deduplicates_same_title_and_artist(sample_tracks):
    duplicate = sample_tracks.iloc[[1]].copy()
    duplicate["track_id"] = "b-remaster"
    extended_tracks = pd.concat([sample_tracks, duplicate], ignore_index=True)
    model = ContentBasedRecommender().fit(extended_tracks)

    result = model.recommend("a", n_recommendations=3, popularity_bias=0)

    labels = result[["track_name", "artists"]].value_counts()
    assert labels.max() == 1
