import pytest

from spotify_recommender.catalog import merge_catalog


def test_catalog_merge_keeps_genres_and_requires_real_audio(sample_tracks):
    chart = (
        sample_tracks.iloc[[0, 1]]
        .rename(columns={"track_id": "spotify_id", "track_name": "name"})
        .copy()
    )
    chart["snapshot_date"] = "2025-06-11"
    chart["album_release_date"] = ["2025-01-01", "2024-01-01"]
    chart.loc[chart.index[1], "spotify_id"] = "new-id"
    chart.loc[chart.index[1], "energy"] = None
    result = merge_catalog(sample_tracks, chart)
    assert result["track_id"].tolist().count("a") == 1
    assert result.loc[result["track_id"].eq("a"), "track_genre"].item() == "pop"
    assert "new-id" not in result["track_id"].tolist()


def test_new_chart_tracks_have_dates_and_honest_unknown_genre(sample_tracks):
    chart = sample_tracks.iloc[[0]].rename(columns={"track_id": "spotify_id", "track_name": "name"})
    chart = chart.copy()
    chart["spotify_id"] = "new-id"
    chart["snapshot_date"] = "2025-06-11"
    chart["album_release_date"] = "2025-02-01"
    result = merge_catalog(sample_tracks, chart)
    new = result.loc[result["track_id"].eq("new-id")].iloc[0]
    assert new["release_year"] == 2025
    assert new["track_genre"] == "unclassified"
    with pytest.raises(ValueError, match="missing columns"):
        merge_catalog(sample_tracks, chart.drop(columns="energy"))
