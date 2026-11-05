import pandas as pd
import pytest

from spotify_recommender.model import ContentBasedRecommender


def test_audio_filters_and_exclusions(sample_tracks):
    model = ContentBasedRecommender().fit(sample_tracks)
    result = model.recommend_from_tracks(
        ["a"], audio_ranges={"energy": (0.5, 1)}, excluded_track_ids=["b"]
    )
    assert result.empty
    assert "reason" in result.columns


def test_filters_search_entire_catalog(sample_tracks):
    many = pd.concat([sample_tracks.iloc[[1]]] * 310, ignore_index=True)
    many["track_id"] = [f"copy-{i}" for i in range(len(many))]
    tracks = pd.concat([sample_tracks, many], ignore_index=True)
    model = ContentBasedRecommender().fit(tracks)
    result = model.recommend_from_tracks(["a"], audio_ranges={"energy": (0, 0.1)})
    assert result["track_id"].tolist() == ["c"]


@pytest.mark.parametrize(
    "ranges",
    [
        {"unknown": (0, 1)},
        {"energy": (1, 0)},
        {"tempo": (0, float("inf"))},
        {"energy": (-0.1, 1)},
        {"valence": (0, 1.1)},
    ],
)
def test_invalid_audio_ranges(sample_tracks, ranges):
    model = ContentBasedRecommender().fit(sample_tracks)
    with pytest.raises(ValueError):
        model.recommend_from_tracks(["a"], audio_ranges=ranges)


def test_all_tracks_excluded(sample_tracks):
    model = ContentBasedRecommender().fit(sample_tracks)
    result = model.recommend_from_tracks(["a"], excluded_track_ids=["b", "c"])
    assert result.empty


def test_release_year_filter_excludes_unknown_years(sample_tracks):
    sample_tracks["release_year"] = [2020, 2024, None]
    model = ContentBasedRecommender().fit(sample_tracks)
    result = model.recommend_from_tracks(["a"], minimum_release_year=2023)
    assert result["track_id"].tolist() == ["b"]


def test_unknown_genre_is_not_evidence_of_similarity(sample_tracks):
    sample_tracks["track_genre"] = "unclassified"
    model = ContentBasedRecommender().fit(sample_tracks)
    result = model.recommend_from_tracks(["a"], n_recommendations=2)
    assert not result["reason"].str.contains("unclassified").any()
    assert model.recommend_from_tracks(["a"], same_genre_only=True).empty
