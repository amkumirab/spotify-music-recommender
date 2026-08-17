# Spotify Music Recommender 🎧

[![CI](https://github.com/amkumirab/spotify-music-recommender/actions/workflows/ci.yml/badge.svg)](https://github.com/amkumirab/spotify-music-recommender/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A portfolio-ready, content-based music recommendation system trained on 114K
Spotify tracks. Blend up to five songs into a taste profile and build a diverse
playlist using audio features, genre information, and cosine similarity.

> This is an educational project. It is not affiliated with or endorsed by Spotify.

## Highlights

- Content-based recommendation with explainable results
- Multi-track taste profiles built from one to five seed songs
- Nine audio signals: energy, valence, danceability, tempo, acousticness, and more
- Maximum Marginal Relevance (MMR) diversity and per-artist limits
- Optional popularity reranking and selected-genre filtering
- Fast interactive Streamlit interface with Spotify deep links
- Downloadable CSV playlists with ranking, match scores, and Spotify links
- Reproducible offline evaluation for relevance, diversity, and catalog coverage
- Reproducible public Kaggle dataset download
- Unit tests, linting, coverage, and GitHub Actions CI
- Full dataset fallback to a small repository sample

## How it works

```mermaid
flowchart LR
    A[Spotify tracks CSV] --> B[Clean and deduplicate]
    B --> C[Standardize audio features]
    B --> D[One-hot encode genre]
    C --> E[Feature matrix]
    D --> E
    I[One to five seed tracks] --> J[Average taste profile]
    E --> J
    J --> F[Cosine nearest neighbours]
    F --> G[Popularity reranking]
    G --> K[MMR diversity + artist cap]
    K --> H[Playlist + explanations]
```

The recommender is deliberately content-based: it does not require user history.
It averages the selected tracks into a single audio-and-genre profile, retrieves
the closest candidates, and applies MMR so the final playlist stays relevant
without becoming repetitive. This also keeps every recommendation explainable.

## Run locally

Clone the repository and enter the project directory:

```bash
git clone https://github.com/amkumirab/spotify-music-recommender.git
cd spotify-music-recommender
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project and development tools:

```bash
python -m pip install -e ".[dev]"
```

The repository includes a balanced sample covering all 114 genres, so the app
can run immediately. To download the complete Kaggle dataset, optionally run:

```bash
python scripts/download_data.py
```

Start the application:

```bash
python -m streamlit run app.py
```

Open `http://localhost:8501`, search for tracks or artists, add one to five seed
tracks, adjust popularity and diversity, and build the playlist. Downloading the
complete dataset gives the best results; otherwise the app automatically uses the
repository sample. Use **Download playlist as CSV** to save the ranked results in
a spreadsheet-friendly format.

## Evaluate recommendation quality

Run the offline benchmark against 25 reproducibly sampled seed tracks:

```bash
python scripts/evaluate_model.py
```

Use the repository sample or save a machine-readable report when needed:

```bash
python scripts/evaluate_model.py \
  --dataset data/sample/spotify_tracks_sample.csv \
  --sample-size 20 \
  --recommendations 10 \
  --output reports/evaluation.json
```

The report contains four complementary quality signals:

- **Mean profile match:** average cosine similarity between seeds and results
- **Artist diversity:** average share of unique primary artists in each playlist
- **Genre diversity:** average share of unique genres in each playlist
- **Catalog coverage:** share of the catalog reached across all evaluated playlists

All ratio metrics range from `0.0` to `1.0`. The random state and ranking settings
are included in the JSON output so benchmark runs can be reproduced exactly.

## Dataset

The project uses the
[Spotify Tracks Dataset | Audio Features](https://www.kaggle.com/datasets/saichaitanyareddyai/spotify-tracks-dataset-audio-features)
from Kaggle. It contains roughly 114K tracks from 114 genres and is listed as CC0.
See [`data/DATASET.md`](data/DATASET.md) for attribution and reproducibility details.

The raw data is not committed to Git. The download script calls Kaggle's public
dataset endpoint and extracts the archive into `data/raw/`.

## Project structure

```text
spotify-music-recommender/
├── .github/workflows/ci.yml
├── data/
│   ├── raw/                    # full Kaggle data (gitignored)
│   ├── sample/                 # small reproducible demo data
│   └── DATASET.md
├── scripts/download_data.py
├── scripts/evaluate_model.py
├── src/spotify_recommender/
│   ├── data.py                 # validation, cleaning, search
│   ├── evaluation.py           # offline recommendation quality metrics
│   ├── export.py               # spreadsheet-friendly playlist export
│   └── model.py                # features, similarity, ranking
├── tests/
├── app.py
└── pyproject.toml
```

## Development

```bash
python -m ruff check .
python -m pytest --cov=spotify_recommender --cov-report=term-missing
```

The GitHub Actions workflow runs the same lint and test checks on every push and
pull request.

## Roadmap

- Learn feature weights from likes/dislikes
- Add Spotify OAuth and export generated playlists
- Package the model behind a FastAPI service

## License

Project code is released under the MIT License. Dataset licensing is documented
separately in [`data/DATASET.md`](data/DATASET.md).
