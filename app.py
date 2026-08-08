"""Streamlit interface for the Spotify music recommender."""

from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from spotify_recommender.data import display_label, find_tracks, load_tracks
from spotify_recommender.model import ContentBasedRecommender

PROJECT_ROOT = Path(__file__).resolve().parent
FULL_DATASET = PROJECT_ROOT / "data" / "raw" / "spotify-tracks-dataset-detailed.csv"
SAMPLE_DATASET = PROJECT_ROOT / "data" / "sample" / "spotify_tracks_sample.csv"


def dataset_path() -> Path:
    return FULL_DATASET if FULL_DATASET.exists() else SAMPLE_DATASET


@st.cache_data(show_spinner=False)
def get_tracks(path: str):
    return load_tracks(path)


@st.cache_resource(show_spinner="Learning the sound of every track…")
def get_model(path: str) -> ContentBasedRecommender:
    tracks = get_tracks(path)
    return ContentBasedRecommender().fit(tracks)


st.set_page_config(page_title="Spotify Music Recommender", page_icon="🎧", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(145deg, #0b0f0d 0%, #121212 55%, #0e2618 100%); }
    [data-testid="stMetric"] { background: #181818; padding: 1rem; border-radius: 14px; }
    .track-card { background:#181818; border:1px solid #2c2c2c; border-radius:16px;
                  padding:1rem 1.1rem; margin:.55rem 0; }
    .track-card:hover { border-color:#1DB954; }
    .score { color:#1DB954; font-weight:700; }
    .muted { color:#b3b3b3; }
    a { color:#1DB954 !important; text-decoration:none; }
    </style>
    """,
    unsafe_allow_html=True,
)

path = dataset_path()
tracks = get_tracks(str(path))
model = get_model(str(path))

st.title("🎧 Spotify Music Recommender")
st.caption("Discover tracks with a content-based machine-learning model — no Spotify login needed.")

metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("Tracks", f"{len(tracks):,}")
metric_b.metric("Artists", f"{tracks['artists'].nunique():,}")
metric_c.metric("Genres", f"{tracks['track_genre'].nunique():,}")

st.divider()
controls, results_column = st.columns([1, 2], gap="large")

with controls:
    st.subheader("Choose your starting track")
    query = st.text_input("Search by song or artist", placeholder="Try: Coldplay")
    matches = find_tracks(tracks, query, limit=30)

    if matches.empty:
        st.warning("No matching tracks. Try another title or artist.")
        st.stop()

    label_to_id = {
        f"{display_label(row)} · {row['track_id'][-5:]}": str(row["track_id"])
        for _, row in matches.iterrows()
    }
    selected_label = st.selectbox("Track", options=list(label_to_id))
    selected_id = label_to_id[selected_label]

    count = st.slider("Number of recommendations", 5, 20, 10)
    popularity_bias = st.slider(
        "Popularity boost",
        min_value=0.0,
        max_value=0.5,
        value=0.1,
        step=0.05,
        help="Increase this to favor well-known tracks while preserving audio similarity.",
    )
    same_genre = st.checkbox("Stay in the same genre")
    recommend = st.button("Find my next tracks", type="primary", use_container_width=True)

with results_column:
    st.subheader("Your recommendations")
    if recommend:
        recommendations = model.recommend(
            selected_id,
            n_recommendations=count,
            popularity_bias=popularity_bias,
            same_genre_only=same_genre,
        )
        if recommendations.empty:
            st.info("No tracks matched these filters. Turn off the genre filter and try again.")
        for rank, row in recommendations.iterrows():
            spotify_url = f"https://open.spotify.com/track/{row['track_id']}"
            track_name = escape(str(row["track_name"]))
            artists = escape(str(row["artists"]))
            genre = escape(str(row["track_genre"]))
            reason = escape(str(row["reason"]))
            st.markdown(
                f"""
                <div class="track-card">
                  <div><strong>{rank + 1}. {track_name}</strong></div>
                  <div class="muted">{artists} · {genre}</div>
                  <div><span class="score">{row['similarity']:.0%} similar</span>
                       · popularity {int(row['popularity'])}/100</div>
                  <div class="muted">{reason}</div>
                  <a href="{spotify_url}" target="_blank">Open in Spotify ↗</a>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Search for a track, adjust the controls, then generate recommendations.")

with st.expander("How does it work?"):
    st.write(
        "The model standardizes nine Spotify audio features, adds a one-hot genre signal, "
        "and finds nearest neighbours using cosine similarity. A small optional popularity "
        "boost reranks the candidates. Every result includes a short explanation."
    )
    st.caption(f"Using: {path.relative_to(PROJECT_ROOT)}")
