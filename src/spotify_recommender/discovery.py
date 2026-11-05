"""Resolve a personal library against the local catalog and avoid known recordings."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def parse_track_links(text: str) -> list[str]:
    if len(text) > 500_000:
        raise ValueError("Paste at most 500 KB of track links.")
    matches = re.findall(
        r"(?:https://open\.spotify\.com/(?:intl-[a-z]+/)?track/|spotify:track:)"
        r"([A-Za-z0-9]{22})(?![A-Za-z0-9])",
        text,
    )
    return list(dict.fromkeys(matches))


def _key(name: str, artists: str) -> tuple[str, str]:
    def normalize(value):
        return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())

    return normalize(name), normalize(str(artists).split(";")[0])


def match_library(likes: list[dict], catalog: pd.DataFrame) -> dict:
    by_id = catalog.set_index("track_id")
    versions: dict[tuple[str, str], list[str]] = {}
    for row in catalog[["track_id", "track_name", "artists"]].itertuples(index=False):
        versions.setdefault(_key(row.track_name, row.artists), []).append(str(row.track_id))
    excluded = set()
    seeds = []
    matched = 0
    missing = []
    for song in sorted(likes, key=lambda song: song.get("added_at", ""), reverse=True):
        track_id = song["track_id"]
        excluded.add(track_id)
        excluded.add(song.get("original_id", track_id))
        same_song = versions.get(_key(song.get("track_name", ""), song.get("artists", "")), [])
        known_id = track_id if track_id in by_id.index else song.get("original_id", track_id)
        if known_id in by_id.index:
            row = by_id.loc[known_id]
            same_song = versions.get(_key(row["track_name"], row["artists"]), [track_id])
            chosen = known_id
        else:
            chosen = same_song[0] if same_song else None
        excluded.update(same_song)
        if chosen is not None:
            matched += 1
            if chosen not in seeds:
                seeds.append(chosen)
        else:
            missing.append(song)
    return {
        "seed_ids": seeds[:50],
        "excluded_ids": sorted(excluded),
        "matched": matched,
        "unmatched": len(missing),
        "missing": missing,
    }
