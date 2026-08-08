"""Download and extract the public Spotify dataset from Kaggle."""

from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

DATASET_SLUG = "saichaitanyareddyai/spotify-tracks-dataset-audio-features"
DOWNLOAD_URL = f"https://www.kaggle.com/api/v1/datasets/download/{DATASET_SLUG}"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
ARCHIVE_PATH = RAW_DIR / "spotify-kaggle.zip"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {DATASET_SLUG}...")
    request = urllib.request.Request(DOWNLOAD_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as response, ARCHIVE_PATH.open("wb") as archive:
        shutil.copyfileobj(response, archive)

    with zipfile.ZipFile(ARCHIVE_PATH) as zipped:
        zipped.extractall(RAW_DIR)
    print(f"Dataset extracted to {RAW_DIR}")


if __name__ == "__main__":
    main()
