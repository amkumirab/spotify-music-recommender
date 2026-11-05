"""Build a pinned, attributed catalog from the base dataset and real chart data."""

from __future__ import annotations

import hashlib
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from spotify_recommender.catalog import merge_catalog
from spotify_recommender.data import load_tracks

ROOT = Path(__file__).resolve().parents[1]
SLUG = "asaniczka/top-spotify-songs-in-73-countries-daily-updated"
VERSION = 608
EXPECTED_SHA256 = "e048c4726c7ffb0c4e50827b459b760e98561f07202d6efb586f69fc962902ef"
MEMBER = "universal_top_spotify_songs.csv"


def main() -> None:
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / f"charts-v{VERSION}.zip"
    if not archive.exists():
        print("Downloading pinned chart snapshot...", flush=True)
        url = (
            f"https://www.kaggle.com/api/v1/datasets/download/{SLUG}?datasetVersionNumber={VERSION}"
        )
        request = urllib.request.Request(url, headers={"User-Agent": "SpotifyCatalog/1.0"})
        partial = archive.with_suffix(".part")
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as target:
            while block := response.read(1024 * 1024):
                target.write(block)
        partial.replace(archive)
    hasher = hashlib.sha256()
    with archive.open("rb") as archive_file:
        while block := archive_file.read(1024 * 1024):
            hasher.update(block)
    digest = hasher.hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Chart archive checksum mismatch; catalog was not changed.")
    observations = []
    latest = ""
    print("Reading chart observations in chunks...", flush=True)
    with zipfile.ZipFile(archive) as zipped:
        with zipped.open(MEMBER) as csv:
            for chunk in pd.read_csv(csv, chunksize=100_000, low_memory=False):
                latest = max(latest, str(chunk["snapshot_date"].max()))
                observations.append(
                    chunk.sort_values("snapshot_date", ascending=False).drop_duplicates(
                        "spotify_id"
                    )
                )
    base = load_tracks(raw / "spotify-tracks-dataset-detailed.csv")
    catalog = merge_catalog(base, pd.concat(observations, ignore_index=True))
    destination = raw / "spotify_catalog.csv"
    temporary = destination.with_suffix(".tmp")
    catalog.to_csv(temporary, index=False)
    load_tracks(temporary)
    temporary.replace(destination)
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "tracks": len(catalog),
        "chart_source": f"https://www.kaggle.com/datasets/{SLUG}",
        "chart_version": VERSION,
        "chart_archive_sha256": digest,
        "latest_chart_observation": latest,
        "latest_release_year_with_audio": int(catalog["release_year"].max()),
        "chart_tracks_with_complete_audio": int(catalog["source"].str.contains("Asaniczka").sum()),
        "base_unique_tracks": len(base),
        "licenses": ["CC0 (base)", "ODC-By (chart snapshot; Asaniczka)"],
        "notes": "Not live data. New chart tracks missing audio features are excluded.",
    }
    (ROOT / "data/catalog_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    # Keep all genres and recent chart examples in a modest, deterministic demo catalog.
    sample = pd.concat(
        [
            base.groupby("track_genre", group_keys=False).head(20),
            catalog[catalog["release_year"].ge(2023)].head(500),
        ]
    ).drop_duplicates("track_id")
    sample = catalog[catalog["track_id"].isin(sample["track_id"])]
    sample.to_csv(ROOT / "data/sample/spotify_tracks_sample.csv", index=False)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
