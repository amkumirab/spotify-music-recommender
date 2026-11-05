"""Merge real chart observations without inventing missing audio features."""

from __future__ import annotations

import pandas as pd

from spotify_recommender.model import AUDIO_FEATURES


def merge_catalog(base: pd.DataFrame, charts: pd.DataFrame) -> pd.DataFrame:
    recent = charts.rename(columns={"spotify_id": "track_id", "name": "track_name"}).copy()
    required = {"track_id", "track_name", "artists", "snapshot_date", *AUDIO_FEATURES}
    if not required.issubset(recent.columns):
        raise ValueError(f"Chart data missing columns: {sorted(required - set(recent.columns))}")
    for column in AUDIO_FEATURES:
        recent[column] = pd.to_numeric(recent[column], errors="coerce")
    recent = recent.dropna(subset=[*AUDIO_FEATURES, "track_id", "track_name", "artists"])
    recent = recent.sort_values("snapshot_date", ascending=False).drop_duplicates("track_id")
    genre_by_id = base.set_index("track_id")["track_genre"]
    recent["track_genre"] = recent["track_id"].map(genre_by_id).fillna("unclassified")
    recent["artists"] = recent["artists"].str.replace(", ", ";", regex=False)
    recent["source"] = "Kaggle charts (Asaniczka)"
    recent["release_year"] = pd.to_numeric(
        recent.get("album_release_date", pd.Series(dtype="string")).astype("string").str[:4],
        errors="coerce",
    )
    original = base.copy()
    original["source"] = "Kaggle 114K (Sai Chaitanya Reddy)"
    return pd.concat([recent, original], ignore_index=True).drop_duplicates("track_id")
