"""Streamlit interface for the Spotify music recommender."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from spotify_recommender.account_ui import render_account
from spotify_recommender.data import load_tracks
from spotify_recommender.model import ContentBasedRecommender
from spotify_recommender.profile_ui import render_manual_profile
from spotify_recommender.spotify_export_ui import render_spotify_export
from spotify_recommender.studio import render_library, render_playlist

PROJECT_ROOT = Path(__file__).resolve().parent
FULL_DATASET = PROJECT_ROOT / "data" / "raw" / "spotify-tracks-dataset-detailed.csv"
UPDATED_DATASET = PROJECT_ROOT / "data" / "raw" / "spotify_catalog.csv"
SAMPLE_DATASET = PROJECT_ROOT / "data" / "sample" / "spotify_tracks_sample.csv"
MAX_SEED_TRACKS = 5


def dataset_path() -> Path:
    if os.environ.get("SPOTIFY_DATASET"):
        return Path(os.environ["SPOTIFY_DATASET"])
    if UPDATED_DATASET.exists():
        return UPDATED_DATASET
    return FULL_DATASET if FULL_DATASET.exists() else SAMPLE_DATASET


@st.cache_data(show_spinner=False)
def get_tracks(path: str, revision: int):
    return load_tracks(path)


@st.cache_resource(show_spinner="Learning the sound of every track…")
def get_model(path: str, revision: int) -> ContentBasedRecommender:
    """Fit the catalog with no shared genre signal for unclassified tracks."""
    tracks = get_tracks(path, revision)
    return ContentBasedRecommender().fit(tracks)


st.set_page_config(page_title="Spotify Music Recommender", page_icon="🎧", layout="wide")

path = dataset_path()
revision = path.stat().st_mtime_ns
tracks = get_tracks(str(path), revision)
model = get_model(str(path), revision)

st.title("🎧 Playlist Studio")
st.caption("Your taste. Songs you haven't saved yet. Discover your next favourites.")
st.caption("Offline audio catalog + optional Spotify connection and private playlist saving.")
if path in (UPDATED_DATASET, SAMPLE_DATASET):
    st.caption(
        "Catalog snapshot: 11 June 2025 · includes 2025 releases · "
        + ("demo sample" if path == SAMPLE_DATASET else "full merged catalog")
    )

metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("Tracks", f"{len(tracks):,}")
metric_b.metric("Artists", f"{tracks['artists'].nunique():,}")
metric_c.metric("Genres", f"{tracks['track_genre'].nunique():,}")

st.divider()
for key, default in {
    "playlist": None,
    "playlist_settings": {},
    "excluded_track_ids": [],
    "seed_track_ids": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default
render_account(tracks)
controls, results_column = st.columns([1, 2], gap="large")

with controls:
    st.subheader("Build your taste profile")
    source = st.radio(
        "Build from",
        ["Selected tracks", "My imported likes"],
        key="profile_source",
        horizontal=True,
    )
    report = st.session_state.get("library_report", {})
    if source == "My imported likes" and not report.get("seed_ids"):
        st.info("Connect and sync Spotify, paste track links, or try the demo in the sidebar.")
    elif source == "My imported likes":
        st.caption(
            "New to your library, not necessarily newly released. Your existing likes are excluded."
        )
    if source == "Selected tracks":
        render_manual_profile(tracks, MAX_SEED_TRACKS)

    count = st.slider("Number of recommendations", 5, 30, 10)
    popularity_bias = st.slider(
        "Popularity boost",
        min_value=0.0,
        max_value=0.5,
        value=0.1,
        step=0.05,
        help="Increase this to favor well-known tracks while preserving audio similarity.",
    )
    diversity = st.slider(
        "Playlist diversity",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.05,
        help="Higher values reduce songs that sound too similar to each other.",
    )
    max_tracks_per_artist = st.select_slider(
        "Maximum tracks per artist",
        options=[1, 2, 3],
        value=2,
    )
    same_genre = st.checkbox("Stay in the selected genres")
    minimum_year = None
    if "release_year" in tracks and tracks["release_year"].notna().any():
        if st.checkbox("Only recent releases", key="recent_only"):
            minimum_year = st.slider("Released since", 2020, 2025, 2023)
            st.caption("Only songs with a known release year qualify. Coverage ends in 2025.")
    audio_ranges = {}
    with st.expander("Shape the sound"):
        if st.checkbox("Use audio filters", key="use_audio_filters"):
            audio_ranges = {
                "energy": st.slider("Energy range", 0.0, 1.0, (0.0, 1.0), step=0.05),
                "valence": st.slider("Mood range", 0.0, 1.0, (0.0, 1.0), step=0.05),
                "tempo": st.slider("Tempo range (BPM)", 0, 400, (0, 400), step=5),
            }
            st.caption("Low valence is more somber; high valence is more upbeat.")
    if st.session_state.excluded_track_ids:
        st.caption(f"Hidden tracks: {len(st.session_state.excluded_track_ids)}")
        if st.button("Restore hidden tracks", key="restore_hidden"):
            st.session_state.excluded_track_ids = []
            st.rerun()
    active_seeds = (
        report.get("seed_ids", [])
        if source == "My imported likes"
        else st.session_state.seed_track_ids
    )
    recommend = st.button(
        "Discover new favourites" if source == "My imported likes" else "Build my playlist",
        key="build_playlist",
        type="primary",
        use_container_width=True,
        disabled=not active_seeds,
    )

settings = {
    "seeds": list(active_seeds),
    "source": source,
    "minimum_release_year": minimum_year,
    "count": count,
    "popularity_bias": popularity_bias,
    "diversity": diversity,
    "max_tracks_per_artist": max_tracks_per_artist,
    "same_genre": same_genre,
    "audio_ranges": {key: list(value) for key, value in audio_ranges.items()},
}
with results_column:
    st.subheader("Your playlist")
    if recommend:
        st.session_state.playlist = model.recommend_from_tracks(
            active_seeds,
            n_recommendations=count,
            popularity_bias=popularity_bias,
            same_genre_only=same_genre,
            diversity=diversity,
            max_tracks_per_artist=max_tracks_per_artist,
            audio_ranges=audio_ranges,
            excluded_track_ids=[
                *st.session_state.excluded_track_ids,
                *report.get("excluded_ids", []),
            ],
            minimum_release_year=minimum_year,
        )
        st.session_state.playlist_settings = settings
    render_playlist(tracks, settings)
    render_spotify_export()
    render_library(os.environ.get("SPOTIFY_LIBRARY", str(PROJECT_ROOT / "data/local/library.db")))

with st.expander("How does it work?"):
    st.write(
        "The model averages the audio and genre vectors of your selected tracks into one "
        "taste profile. It finds candidates with cosine similarity, applies an optional "
        "popularity boost, and uses Maximum Marginal Relevance to keep the playlist diverse. "
        "Every result includes a short explanation."
    )
    st.caption(f"Using: {path.name}")
