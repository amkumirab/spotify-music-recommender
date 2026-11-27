import pandas as pd
import pytest

from spotify_recommender.library import PlaylistLibrary
from spotify_recommender.model import ContentBasedRecommender


def test_feedback_persists_and_can_be_updated_or_undone(tmp_path, sample_tracks):
    path = tmp_path / "library.db"
    library = PlaylistLibrary(path)
    tracks = ContentBasedRecommender().fit(sample_tracks).recommend("a", 2)
    snapshot = library.save("Evening mix", tracks, {"seeds": ["a"]})
    assert library.list_feedback() == {}

    library.set_feedback("b", 1)
    library.set_feedback("c", -1)
    reopened = PlaylistLibrary(path)
    assert reopened.list_feedback() == {"b": 1, "c": -1}
    reopened.set_feedback("b", -1)
    reopened.clear_feedback("c")
    assert library.list_feedback() == {"b": -1}
    assert library.load(snapshot)["name"] == "Evening mix"


@pytest.mark.parametrize(("track_id", "rating"), [("", 1), ("b", 0), ("b", True), ("b", 2)])
def test_invalid_feedback_is_not_stored(tmp_path, track_id, rating):
    library = PlaylistLibrary(tmp_path / "library.db")
    with pytest.raises(ValueError, match="Feedback"):
        library.set_feedback(track_id, rating)
    assert library.list_feedback() == {}


@pytest.mark.parametrize("rating", [1, -1])
def test_feedback_changes_score_without_rewriting_seed_similarity(sample_tracks, rating):
    copy = sample_tracks.iloc[[1]].assign(
        track_id="d", track_name="Summer Reprise", artists="Artist D"
    )
    model = ContentBasedRecommender().fit(pd.concat([sample_tracks, copy]))
    options = {"n_recommendations": 4, "popularity_bias": 0, "diversity": 0}
    baseline = model.recommend_from_tracks(["a"], **options).set_index("track_id")
    result = model.recommend_from_tracks(
        ["a"], feedback={"b": rating}, **options
    ).set_index("track_id")
    assert result.loc["d", "similarity"] == pytest.approx(baseline.loc["d", "similarity"])
    shift = result.loc["d", "score"] - baseline.loc["d", "score"]
    assert 0 < rating * shift <= 0.150001
    assert result.loc["c", "score"] == pytest.approx(baseline.loc["c", "score"])


def test_feedback_changes_ranking_and_respects_exclusions(sample_tracks):
    copy = sample_tracks.iloc[[1]].assign(
        track_id="d", track_name="Summer Reprise", artists="Artist D", popularity=67
    )
    sample_tracks.loc[sample_tracks["track_id"].eq("c"), "popularity"] = 68
    model = ContentBasedRecommender().fit(pd.concat([sample_tracks, copy]))
    settings = {"n_recommendations": 1, "popularity_bias": 1, "diversity": 0}
    assert model.recommend_from_tracks(["a"], **settings).iloc[0]["track_id"] == "b"
    assert (
        model.recommend_from_tracks(["a"], feedback={"c": 1}, **settings)
        .iloc[0]["track_id"] == "c"
    )
    filtered = model.recommend_from_tracks(
        ["a"], feedback={"c": 1, "d": 1}, excluded_track_ids=["d"], same_genre_only=True,
        **settings,
    )
    assert filtered["track_id"].tolist() == ["b"]


def test_feedback_missing_from_the_current_catalog_does_not_change_results(sample_tracks):
    model = ContentBasedRecommender().fit(sample_tracks)
    baseline = model.recommend_from_tracks(["a"])
    assert model.recommend_from_tracks(["a"], feedback={"missing": -1}).equals(baseline)
    filtered = model.recommend_from_tracks(
        ["a"], feedback={"b": 1}, excluded_track_ids=["b", "c"]
    )
    assert filtered.empty
