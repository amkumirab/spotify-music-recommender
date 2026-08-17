from __future__ import annotations

import pandas as pd
import pytest

from spotify_recommender.evaluation import EvaluationReport, evaluate_recommender
from spotify_recommender.model import ContentBasedRecommender


def test_evaluate_recommender_aggregates_quality_metrics(sample_tracks):
    model = ContentBasedRecommender().fit(sample_tracks)

    report = evaluate_recommender(
        model,
        ["a", "a", "b"],
        n_recommendations=2,
        popularity_bias=0,
        diversity=0,
        max_tracks_per_artist=None,
    )

    assert report.seeds_evaluated == 2
    assert report.recommendations_generated == 4
    assert 0 <= report.mean_profile_match <= 1
    assert report.artist_diversity == 1
    assert report.genre_diversity == 1
    assert report.catalog_coverage == 1
    assert report.as_dict()["seeds_evaluated"] == 2


def test_evaluate_recommender_handles_empty_result_lists(sample_tracks, monkeypatch):
    model = ContentBasedRecommender().fit(sample_tracks)
    monkeypatch.setattr(model, "recommend", lambda *_args, **_kwargs: pd.DataFrame())

    report = evaluate_recommender(model, ["a"])

    assert report == EvaluationReport(1, 0, 0.0, 0.0, 0.0, 0.0)


def test_evaluate_recommender_validates_inputs(sample_tracks):
    model = ContentBasedRecommender()
    with pytest.raises(RuntimeError, match="fit"):
        evaluate_recommender(model, ["a"])

    model.fit(sample_tracks)
    with pytest.raises(TypeError, match="sequence"):
        evaluate_recommender(model, "a")
    with pytest.raises(ValueError, match="at least one"):
        evaluate_recommender(model, [])
    with pytest.raises(ValueError, match="at least 1"):
        evaluate_recommender(model, ["a"], n_recommendations=0)
