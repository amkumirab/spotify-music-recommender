"""Content-based nearest-neighbour recommender."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import OneHotEncoder, StandardScaler

AUDIO_FEATURES = [
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
]

FEATURE_LABELS = {
    "danceability": "danceability",
    "energy": "energy",
    "loudness": "loudness",
    "speechiness": "speechiness",
    "acousticness": "acoustic sound",
    "instrumentalness": "instrumental feel",
    "liveness": "live feel",
    "valence": "mood",
    "tempo": "tempo",
}


class ContentBasedRecommender:
    """Recommend tracks using audio similarity, genre, and optional popularity reranking."""

    def __init__(self, genre_weight: float = 0.75) -> None:
        if genre_weight < 0:
            raise ValueError("genre_weight must be non-negative")
        self.genre_weight = genre_weight
        self.scaler = StandardScaler()
        self.genre_encoder = OneHotEncoder(handle_unknown="ignore")
        self.neighbors = NearestNeighbors(metric="cosine", algorithm="brute")
        self.tracks: pd.DataFrame | None = None
        self.matrix: sparse.csr_matrix | None = None
        self._track_positions: dict[str, int] = {}

    def fit(self, tracks: pd.DataFrame) -> ContentBasedRecommender:
        """Fit the feature transformers and nearest-neighbour index."""
        if tracks.empty:
            raise ValueError("Cannot fit the recommender with an empty dataset")

        required = set(AUDIO_FEATURES) | {
            "track_id",
            "track_name",
            "artists",
            "track_genre",
            "popularity",
        }
        missing = required.difference(tracks.columns)
        if missing:
            raise ValueError(f"Tracks are missing required columns: {sorted(missing)}")

        self.tracks = tracks.reset_index(drop=True).copy()
        audio = sparse.csr_matrix(self.scaler.fit_transform(self.tracks[AUDIO_FEATURES]))
        genre = self.genre_encoder.fit_transform(self.tracks[["track_genre"]])
        self.matrix = sparse.hstack(
            [audio, genre.multiply(self.genre_weight)], format="csr"
        )
        self.neighbors.fit(self.matrix)
        self._track_positions = {
            str(track_id): position
            for position, track_id in enumerate(self.tracks["track_id"])
        }
        return self

    def recommend(
        self,
        track_id: str,
        n_recommendations: int = 10,
        popularity_bias: float = 0.1,
        same_genre_only: bool = False,
    ) -> pd.DataFrame:
        """Return ranked recommendations for a track ID with readable explanations."""
        if self.tracks is None or self.matrix is None:
            raise RuntimeError("Call fit() before recommend()")
        if track_id not in self._track_positions:
            raise KeyError(f"Unknown track_id: {track_id}")
        if n_recommendations < 1:
            raise ValueError("n_recommendations must be at least 1")
        if not 0 <= popularity_bias <= 1:
            raise ValueError("popularity_bias must be between 0 and 1")

        source_position = self._track_positions[track_id]
        source = self.tracks.iloc[source_position]
        pool_size = min(len(self.tracks), max(100, n_recommendations * 20))
        distances, positions = self.neighbors.kneighbors(
            self.matrix[source_position], n_neighbors=pool_size
        )

        candidates = self.tracks.iloc[positions[0]].copy()
        candidates["similarity"] = 1 - distances[0]
        candidates = candidates[candidates["track_id"] != track_id]
        if same_genre_only:
            candidates = candidates[candidates["track_genre"] == source["track_genre"]]

        popularity = candidates["popularity"].clip(0, 100) / 100
        candidates["score"] = (
            (1 - popularity_bias) * candidates["similarity"]
            + popularity_bias * popularity
        )
        candidates["reason"] = candidates.apply(
            lambda candidate: self._explain(source, candidate), axis=1
        )
        candidates = (
            candidates.sort_values("score", ascending=False)
            .drop_duplicates(subset=["track_name", "artists"], keep="first")
            .head(n_recommendations)
        )
        candidates["similarity"] = candidates["similarity"].clip(0, 1)

        columns = [
            "track_id",
            "track_name",
            "artists",
            "track_genre",
            "popularity",
            "similarity",
            "score",
            "reason",
        ]
        return candidates[columns].reset_index(drop=True)

    def _explain(self, source: pd.Series, candidate: pd.Series) -> str:
        source_values = self.scaler.transform(
            pd.DataFrame([source[AUDIO_FEATURES].to_dict()])
        )[0]
        candidate_values = self.scaler.transform(
            pd.DataFrame([candidate[AUDIO_FEATURES].to_dict()])
        )[0]
        differences = np.abs(source_values - candidate_values)
        closest = np.argsort(differences)[:2]
        reasons = [FEATURE_LABELS[AUDIO_FEATURES[index]] for index in closest]
        if source["track_genre"] == candidate["track_genre"]:
            reasons.insert(0, f"same {source['track_genre']} genre")
        return "Similar " + ", ".join(reasons)
