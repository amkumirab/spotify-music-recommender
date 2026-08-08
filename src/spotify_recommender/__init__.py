"""Content-based music recommendation package."""

from spotify_recommender.data import load_tracks
from spotify_recommender.model import ContentBasedRecommender

__all__ = ["ContentBasedRecommender", "load_tracks"]
__version__ = "0.1.0"
