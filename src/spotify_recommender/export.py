"""Playlist export utilities."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "track_id",
    "track_name",
    "artists",
    "track_genre",
    "popularity",
    "similarity",
}
EXPORT_COLUMNS = [
    "rank",
    "track_name",
    "artists",
    "genre",
    "profile_match_percent",
    "popularity",
    "spotify_url",
]


def build_playlist_export(recommendations: pd.DataFrame) -> pd.DataFrame:
    """Return a spreadsheet-friendly view of ranked recommendations."""
    missing = sorted(REQUIRED_COLUMNS.difference(recommendations.columns))
    if missing:
        raise ValueError(f"Recommendations are missing required columns: {', '.join(missing)}")

    playlist = recommendations[
        ["track_id", "track_name", "artists", "track_genre", "popularity", "similarity"]
    ].copy()
    playlist.insert(0, "rank", range(1, len(playlist) + 1))
    playlist["similarity"] = playlist["similarity"].clip(0, 1).mul(100).round(1)
    playlist["spotify_url"] = (
        "https://open.spotify.com/track/" + playlist["track_id"].astype(str)
    )
    playlist = playlist.rename(
        columns={"track_genre": "genre", "similarity": "profile_match_percent"}
    )

    return playlist[EXPORT_COLUMNS]
