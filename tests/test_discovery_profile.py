import pandas as pd

from spotify_recommender.discovery import match_library, parse_track_links


def test_library_matching_excludes_relinked_versions(sample_tracks):
    likes = [
        {"track_id": "other-version", "track_name": "Bright Morning", "artists": "Artist A"},
        {"track_id": "missing", "track_name": "Unknown", "artists": "Unknown"},
    ]
    report = match_library(likes, sample_tracks)
    assert report["seed_ids"] == ["a"]
    assert set(report["excluded_ids"]) == {"a", "other-version", "missing"}
    assert report["matched"] == 1
    assert report["unmatched"] == 1


def test_pasted_links_are_validated_and_deduplicated():
    first, second = "a" * 22, "b" * 22
    assert parse_track_links(
        f"https://open.spotify.com/track/{first}?si=test\nspotify:track:{second}\n"
        f"spotify:track:{first}\nhttps://evil.test/track/{second}"
    ) == [first, second]


def test_all_known_versions_excluded(sample_tracks):
    duplicate = sample_tracks.iloc[[0]].copy()
    duplicate["track_id"] = "remaster"
    report = match_library([sample_tracks.iloc[0].to_dict()], pd.concat([sample_tracks, duplicate]))
    assert {"a", "remaster"}.issubset(report["excluded_ids"])
