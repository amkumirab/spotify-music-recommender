"""Dataset loading and validation utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "track_id",
    "artists",
    "track_name",
    "popularity",
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "track_genre",
}

NUMERIC_COLUMNS = [
    "popularity",
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


def load_tracks(path: str | Path) -> pd.DataFrame:
    """Load, validate, and lightly clean a Spotify tracks CSV file."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    tracks = pd.read_csv(csv_path, low_memory=False)
    missing = REQUIRED_COLUMNS.difference(tracks.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    tracks = tracks.copy()
    for column in ("track_id", "artists", "track_name", "track_genre"):
        tracks[column] = tracks[column].astype("string").str.strip()

    tracks = tracks.dropna(subset=["track_id", "artists", "track_name", "track_genre"])
    tracks = tracks[
        tracks["track_id"].ne("")
        & tracks["track_name"].ne("")
        & tracks["artists"].ne("")
    ]

    for column in NUMERIC_COLUMNS:
        tracks[column] = pd.to_numeric(tracks[column], errors="coerce")
        median = tracks[column].median()
        tracks[column] = tracks[column].fillna(0 if pd.isna(median) else median)

    # The same track can appear under more than one genre. Keep the most popular row.
    tracks = (
        tracks.sort_values("popularity", ascending=False)
        .drop_duplicates(subset="track_id", keep="first")
        .reset_index(drop=True)
    )
    return tracks


def find_tracks(tracks: pd.DataFrame, query: str, limit: int = 25) -> pd.DataFrame:
    """Return popular title/artist matches for the app's search box."""
    normalized = query.strip().casefold()
    if not normalized:
        return tracks.nlargest(limit, "popularity")

    title_matches = tracks["track_name"].str.casefold().str.contains(
        normalized, regex=False, na=False
    )
    artist_matches = tracks["artists"].str.casefold().str.contains(
        normalized, regex=False, na=False
    )
    return tracks[title_matches | artist_matches].nlargest(limit, "popularity")


def display_label(row: pd.Series) -> str:
    """Build a readable and stable label for a track selector."""
    return f"{row['track_name']} — {row['artists']} · {row['track_genre']}"
