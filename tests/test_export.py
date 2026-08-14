from __future__ import annotations

import pandas as pd
import pytest

from spotify_recommender.export import EXPORT_COLUMNS, build_playlist_export


def test_build_playlist_export_formats_ranked_tracks():
    recommendations = pd.DataFrame(
        {
            "track_id": ["track-one", "track-two"],
            "track_name": ["First Song", "Second Song"],
            "artists": ["Artist A", "Artist B"],
            "track_genre": ["pop", "rock"],
            "popularity": [81, 64],
            "similarity": [0.956, 1.2],
            "reason": ["Shared energy", "Shared tempo"],
        }
    )
    original = recommendations.copy(deep=True)

    playlist = build_playlist_export(recommendations)

    assert list(playlist.columns) == EXPORT_COLUMNS
    assert playlist["rank"].tolist() == [1, 2]
    assert playlist["profile_match_percent"].tolist() == [95.6, 100.0]
    assert playlist["spotify_url"].tolist() == [
        "https://open.spotify.com/track/track-one",
        "https://open.spotify.com/track/track-two",
    ]
    pd.testing.assert_frame_equal(recommendations, original)


def test_build_playlist_export_rejects_missing_columns():
    with pytest.raises(ValueError, match="missing required columns: artists"):
        build_playlist_export(
            pd.DataFrame(
                {
                    "track_id": ["track-one"],
                    "track_name": ["First Song"],
                    "track_genre": ["pop"],
                    "popularity": [81],
                    "similarity": [0.95],
                }
            )
        )
