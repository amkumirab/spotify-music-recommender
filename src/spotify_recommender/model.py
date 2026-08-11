"""Content-based nearest-neighbour recommender."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity
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
        diversity: float = 0.0,
        max_tracks_per_artist: int | None = None,
    ) -> pd.DataFrame:
        """Return recommendations for one track while preserving the original API."""
        return self.recommend_from_tracks(
            [track_id],
            n_recommendations=n_recommendations,
            popularity_bias=popularity_bias,
            same_genre_only=same_genre_only,
            diversity=diversity,
            max_tracks_per_artist=max_tracks_per_artist,
        )

    def recommend_from_tracks(
        self,
        track_ids: Sequence[str],
        n_recommendations: int = 10,
        popularity_bias: float = 0.1,
        same_genre_only: bool = False,
        diversity: float = 0.25,
        max_tracks_per_artist: int | None = 2,
    ) -> pd.DataFrame:
        """Recommend from a combined profile of one or more seed tracks.

        Candidate relevance is calculated against the mean seed vector. Maximum
        Marginal Relevance (MMR) then balances that relevance with result diversity.
        """
        if self.tracks is None or self.matrix is None:
            raise RuntimeError("Call fit() before recommend()")
        if isinstance(track_ids, str):
            raise TypeError("track_ids must be a sequence of track IDs, not a string")

        unique_track_ids = list(dict.fromkeys(str(track_id) for track_id in track_ids))
        if not unique_track_ids:
            raise ValueError("Select at least one seed track")

        unknown = [
            track_id
            for track_id in unique_track_ids
            if track_id not in self._track_positions
        ]
        if unknown:
            raise KeyError(f"Unknown track_id: {unknown[0]}")
        if n_recommendations < 1:
            raise ValueError("n_recommendations must be at least 1")
        if not 0 <= popularity_bias <= 1:
            raise ValueError("popularity_bias must be between 0 and 1")
        if not 0 <= diversity <= 1:
            raise ValueError("diversity must be between 0 and 1")
        if max_tracks_per_artist is not None and max_tracks_per_artist < 1:
            raise ValueError("max_tracks_per_artist must be at least 1")

        source_positions = [self._track_positions[track_id] for track_id in unique_track_ids]
        sources = self.tracks.iloc[source_positions]
        profile = sparse.csr_matrix(self.matrix[source_positions].mean(axis=0))
        pool_size = min(len(self.tracks), max(200, n_recommendations * 30))
        distances, positions = self.neighbors.kneighbors(
            profile, n_neighbors=pool_size
        )

        candidates = self.tracks.iloc[positions[0]].copy()
        candidates["_matrix_position"] = candidates.index.astype(int)
        candidates["similarity"] = 1 - distances[0]
        candidates = candidates[~candidates["track_id"].isin(unique_track_ids)]
        if same_genre_only:
            source_genres = set(sources["track_genre"])
            candidates = candidates[candidates["track_genre"].isin(source_genres)]

        popularity = candidates["popularity"].clip(0, 100) / 100
        candidates["score"] = (
            (1 - popularity_bias) * candidates["similarity"]
            + popularity_bias * popularity
        )
        candidates["reason"] = candidates.apply(
            lambda candidate: self._explain_sources(sources, candidate), axis=1
        )
        candidates = (
            candidates.sort_values("score", ascending=False)
            .drop_duplicates(subset=["track_name", "artists"], keep="first")
        )
        candidates = self._select_diverse(
            candidates,
            n_recommendations=n_recommendations,
            diversity=diversity,
            max_tracks_per_artist=max_tracks_per_artist,
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

    def _select_diverse(
        self,
        candidates: pd.DataFrame,
        n_recommendations: int,
        diversity: float,
        max_tracks_per_artist: int | None,
    ) -> pd.DataFrame:
        """Select candidates with Maximum Marginal Relevance and an artist cap."""
        if candidates.empty or self.matrix is None:
            return candidates.head(0)

        positions = candidates["_matrix_position"].astype(int).to_list()
        pairwise_similarity = cosine_similarity(self.matrix[positions])
        selected: list[int] = []
        artist_counts: dict[str, int] = {}

        while len(selected) < min(n_recommendations, len(candidates)):
            eligible: list[int] = []
            for index, candidate in candidates.iterrows():
                local_index = candidates.index.get_loc(index)
                if local_index in selected:
                    continue
                artist = self._primary_artist(str(candidate["artists"]))
                if (
                    max_tracks_per_artist is not None
                    and artist_counts.get(artist, 0) >= max_tracks_per_artist
                ):
                    continue
                eligible.append(local_index)

            if not eligible:
                break

            def mmr_score(index: int) -> float:
                relevance = float(candidates.iloc[index]["score"])
                redundancy = (
                    max(float(pairwise_similarity[index, chosen]) for chosen in selected)
                    if selected
                    else 0.0
                )
                return (1 - diversity) * relevance - diversity * max(0.0, redundancy)

            best = max(eligible, key=mmr_score)
            selected.append(best)
            artist = self._primary_artist(str(candidates.iloc[best]["artists"]))
            artist_counts[artist] = artist_counts.get(artist, 0) + 1

        return candidates.iloc[selected].copy()

    @staticmethod
    def _primary_artist(artists: str) -> str:
        return artists.split(";", maxsplit=1)[0].strip().casefold()

    def _explain_sources(self, sources: pd.DataFrame, candidate: pd.Series) -> str:
        if len(sources) == 1:
            return self._explain(sources.iloc[0], candidate)

        source_values = self.scaler.transform(sources[AUDIO_FEATURES])
        candidate_values = self.scaler.transform(
            pd.DataFrame([candidate[AUDIO_FEATURES].to_dict()])
        )[0]
        differences = np.abs(source_values - candidate_values)
        closest_source_index = int(np.argmin(differences.mean(axis=1)))
        closest_source = sources.iloc[closest_source_index]
        closest_features = np.argsort(differences[closest_source_index])[:2]
        reasons = [FEATURE_LABELS[AUDIO_FEATURES[index]] for index in closest_features]
        if candidate["track_genre"] in set(sources["track_genre"]):
            reasons.insert(0, f"selected {candidate['track_genre']} genre")
        return f"Matches {closest_source['track_name']} on " + ", ".join(reasons)

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
