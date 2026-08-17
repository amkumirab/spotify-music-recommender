"""Offline quality metrics for recommendation lists."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from statistics import fmean

from spotify_recommender.model import ContentBasedRecommender


@dataclass(frozen=True)
class EvaluationReport:
    """Aggregated measurements from a repeatable recommendation run."""

    seeds_evaluated: int
    recommendations_generated: int
    mean_profile_match: float
    artist_diversity: float
    genre_diversity: float
    catalog_coverage: float

    def as_dict(self) -> dict[str, int | float]:
        """Return a JSON-serializable representation of the report."""
        return asdict(self)


def evaluate_recommender(
    model: ContentBasedRecommender,
    seed_track_ids: Sequence[str],
    *,
    n_recommendations: int = 10,
    popularity_bias: float = 0.1,
    diversity: float = 0.25,
    max_tracks_per_artist: int | None = 2,
) -> EvaluationReport:
    """Evaluate relevance, list diversity, and catalog coverage across seed tracks."""
    if model.tracks is None:
        raise RuntimeError("Call fit() before evaluation")
    if isinstance(seed_track_ids, str):
        raise TypeError("seed_track_ids must be a sequence of track IDs, not a string")
    if n_recommendations < 1:
        raise ValueError("n_recommendations must be at least 1")

    unique_seed_ids = list(dict.fromkeys(str(track_id) for track_id in seed_track_ids))
    if not unique_seed_ids:
        raise ValueError("Provide at least one seed track")

    recommendation_lists = [
        model.recommend(
            track_id,
            n_recommendations=n_recommendations,
            popularity_bias=popularity_bias,
            diversity=diversity,
            max_tracks_per_artist=max_tracks_per_artist,
        )
        for track_id in unique_seed_ids
    ]
    non_empty_lists = [
        recommendations for recommendations in recommendation_lists if len(recommendations)
    ]

    if not non_empty_lists:
        return EvaluationReport(
            seeds_evaluated=len(unique_seed_ids),
            recommendations_generated=0,
            mean_profile_match=0.0,
            artist_diversity=0.0,
            genre_diversity=0.0,
            catalog_coverage=0.0,
        )

    similarities = [
        float(similarity)
        for recommendations in non_empty_lists
        for similarity in recommendations["similarity"]
    ]
    artist_diversity = [
        recommendations["artists"]
        .astype(str)
        .str.split(";", n=1)
        .str[0]
        .str.strip()
        .str.casefold()
        .nunique()
        / len(recommendations)
        for recommendations in non_empty_lists
    ]
    genre_diversity = [
        recommendations["track_genre"].nunique() / len(recommendations)
        for recommendations in non_empty_lists
    ]
    recommended_track_ids = {
        str(track_id)
        for recommendations in non_empty_lists
        for track_id in recommendations["track_id"]
    }

    return EvaluationReport(
        seeds_evaluated=len(unique_seed_ids),
        recommendations_generated=sum(len(result) for result in recommendation_lists),
        mean_profile_match=fmean(similarities),
        artist_diversity=fmean(artist_diversity),
        genre_diversity=fmean(genre_diversity),
        catalog_coverage=len(recommended_track_ids) / len(model.tracks),
    )
