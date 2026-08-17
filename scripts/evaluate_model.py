"""Run a reproducible offline evaluation of the recommender."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from spotify_recommender.data import load_tracks
from spotify_recommender.evaluation import evaluate_recommender
from spotify_recommender.model import ContentBasedRecommender

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FULL_DATASET = PROJECT_ROOT / "data" / "raw" / "spotify-tracks-dataset-detailed.csv"
SAMPLE_DATASET = PROJECT_ROOT / "data" / "sample" / "spotify_tracks_sample.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure recommendation relevance, diversity, and catalog coverage."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        help="CSV dataset path. Defaults to the full dataset when available.",
    )
    parser.add_argument("--sample-size", type=int, default=25, help="Number of seed tracks.")
    parser.add_argument(
        "--recommendations", type=int, default=10, help="Recommendations per seed track."
    )
    parser.add_argument("--random-state", type=int, default=42, help="Sampling seed.")
    parser.add_argument("--popularity-bias", type=float, default=0.1)
    parser.add_argument("--diversity", type=float, default=0.25)
    parser.add_argument("--max-tracks-per-artist", type=int, default=2)
    parser.add_argument("--output", type=Path, help="Optional path for the JSON report.")
    args = parser.parse_args()
    if args.sample_size < 1:
        parser.error("--sample-size must be at least 1")
    if args.recommendations < 1:
        parser.error("--recommendations must be at least 1")
    return args


def main() -> None:
    args = parse_args()
    dataset_path = args.dataset or (FULL_DATASET if FULL_DATASET.exists() else SAMPLE_DATASET)
    tracks = load_tracks(dataset_path)
    sample_size = min(args.sample_size, len(tracks))
    seed_track_ids = (
        tracks.sample(n=sample_size, random_state=args.random_state)["track_id"]
        .astype(str)
        .tolist()
    )

    model = ContentBasedRecommender().fit(tracks)
    report = evaluate_recommender(
        model,
        seed_track_ids,
        n_recommendations=args.recommendations,
        popularity_bias=args.popularity_bias,
        diversity=args.diversity,
        max_tracks_per_artist=args.max_tracks_per_artist,
    )
    resolved_dataset = dataset_path.resolve()
    try:
        dataset_label = resolved_dataset.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        dataset_label = str(resolved_dataset)
    payload = {
        "dataset": dataset_label,
        "catalog_tracks": len(tracks),
        "settings": {
            "sample_size": sample_size,
            "recommendations": args.recommendations,
            "random_state": args.random_state,
            "popularity_bias": args.popularity_bias,
            "diversity": args.diversity,
            "max_tracks_per_artist": args.max_tracks_per_artist,
        },
        "metrics": report.as_dict(),
    }
    rendered_report = json.dumps(payload, indent=2)
    print(rendered_report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered_report + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
