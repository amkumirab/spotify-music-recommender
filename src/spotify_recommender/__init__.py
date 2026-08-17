"""Content-based music recommendation package."""

from spotify_recommender.data import load_tracks
from spotify_recommender.evaluation import EvaluationReport, evaluate_recommender
from spotify_recommender.model import ContentBasedRecommender

__all__ = [
    "ContentBasedRecommender",
    "EvaluationReport",
    "evaluate_recommender",
    "load_tracks",
]
__version__ = "0.1.0"
