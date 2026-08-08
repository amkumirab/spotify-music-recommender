from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def sample_tracks() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "track_id": "a",
                "artists": "Artist A",
                "track_name": "Bright Morning",
                "popularity": 50,
                "danceability": 0.80,
                "energy": 0.75,
                "loudness": -5.0,
                "speechiness": 0.05,
                "acousticness": 0.10,
                "instrumentalness": 0.00,
                "liveness": 0.12,
                "valence": 0.85,
                "tempo": 120.0,
                "track_genre": "pop",
            },
            {
                "track_id": "b",
                "artists": "Artist B",
                "track_name": "Summer Light",
                "popularity": 70,
                "danceability": 0.78,
                "energy": 0.72,
                "loudness": -5.2,
                "speechiness": 0.06,
                "acousticness": 0.12,
                "instrumentalness": 0.00,
                "liveness": 0.10,
                "valence": 0.82,
                "tempo": 121.0,
                "track_genre": "pop",
            },
            {
                "track_id": "c",
                "artists": "Artist C",
                "track_name": "Quiet Piano",
                "popularity": 30,
                "danceability": 0.20,
                "energy": 0.10,
                "loudness": -18.0,
                "speechiness": 0.03,
                "acousticness": 0.95,
                "instrumentalness": 0.92,
                "liveness": 0.08,
                "valence": 0.20,
                "tempo": 70.0,
                "track_genre": "classical",
            },
        ]
    )
