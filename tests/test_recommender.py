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


def test_multi_track_profile_excludes_all_seed_tracks(sample_tracks):
    model = ContentBasedRecommender().fit(sample_tracks)

    result = model.recommend_from_tracks(
        ["a", "c"], n_recommendations=2, popularity_bias=0, diversity=0
    )

    assert set(result["track_id"]).isdisjoint({"a", "c"})
    assert result.iloc[0]["reason"].startswith("Matches")


def test_multi_track_profile_caps_tracks_per_artist(sample_tracks):
    extra_tracks = []
    for track_id, artist in (("d", "Artist D"), ("e", "Artist E"), ("f", "Artist B")):
        track = sample_tracks.iloc[1].copy()
        track["track_id"] = track_id
        track["track_name"] = f"Variation {track_id}"
        track["artists"] = artist
        extra_tracks.append(track)
    tracks = pd.concat([sample_tracks, pd.DataFrame(extra_tracks)], ignore_index=True)
    model = ContentBasedRecommender().fit(tracks)

    result = model.recommend_from_tracks(
        ["a"],
        n_recommendations=4,
        popularity_bias=0,
        diversity=0.3,
        max_tracks_per_artist=1,
    )

    primary_artists = result["artists"].str.split(";").str[0]
    assert primary_artists.nunique() == len(result)


def test_multi_track_profile_filters_to_selected_genres(sample_tracks):
    model = ContentBasedRecommender().fit(sample_tracks)

    result = model.recommend_from_tracks(
        ["a"], n_recommendations=5, same_genre_only=True
    )

    assert set(result["track_genre"]) == {"pop"}


def test_recommender_validates_fit_and_profile_inputs(sample_tracks):
    with pytest.raises(ValueError, match="non-negative"):
        ContentBasedRecommender(genre_weight=-1)
    with pytest.raises(ValueError, match="empty dataset"):
        ContentBasedRecommender().fit(pd.DataFrame())
    with pytest.raises(ValueError, match="missing required columns"):
        ContentBasedRecommender().fit(sample_tracks.drop(columns="tempo"))
    with pytest.raises(RuntimeError, match=r"fit\(\)"):
        ContentBasedRecommender().recommend_from_tracks(["a"])

    model = ContentBasedRecommender().fit(sample_tracks)
    with pytest.raises(TypeError, match="sequence"):
        model.recommend_from_tracks("a")
    with pytest.raises(ValueError, match="at least one seed"):
        model.recommend_from_tracks([])
    with pytest.raises(KeyError, match="Unknown track_id"):
        model.recommend_from_tracks(["missing"])


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"n_recommendations": 0}, "at least 1"),
        ({"popularity_bias": 1.1}, "between 0 and 1"),
        ({"diversity": -0.1}, "between 0 and 1"),
        ({"max_tracks_per_artist": 0}, "at least 1"),
    ],
)
def test_multi_track_profile_validates_ranking_options(sample_tracks, kwargs, message):
    model = ContentBasedRecommender().fit(sample_tracks)

    with pytest.raises(ValueError, match=message):
        model.recommend_from_tracks(["a"], **kwargs)
