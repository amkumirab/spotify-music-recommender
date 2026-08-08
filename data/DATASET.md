# Dataset

This project uses **Spotify Tracks Dataset | Audio Features** by Sai Chaitanya
Reddy, downloaded from Kaggle on 2026-08-07.

- Source: https://www.kaggle.com/datasets/saichaitanyareddyai/spotify-tracks-dataset-audio-features
- Kaggle slug: `saichaitanyareddyai/spotify-tracks-dataset-audio-features`
- License: CC0 / Public Domain (as stated on the Kaggle dataset page)
- Size: approximately 114,000 tracks, 20 columns, and 114 genres

The full CSV is stored in `data/raw/` and intentionally excluded from Git to keep
the repository lightweight. Run `python scripts/download_data.py` to reproduce the
download. The tracked file in `data/sample/` is a small sample for quick demos and CI.
