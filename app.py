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
MAX_SEED_TRACKS = 5


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
st.caption(
    "Blend up to five songs into one taste profile, then discover a diverse playlist."
)

metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("Tracks", f"{len(tracks):,}")
metric_b.metric("Artists", f"{tracks['artists'].nunique():,}")
metric_c.metric("Genres", f"{tracks['track_genre'].nunique():,}")

st.divider()
controls, results_column = st.columns([1, 2], gap="large")

with controls:
    st.subheader("Build your taste profile")
    query = st.text_input("Search by song or artist", placeholder="Try: Coldplay")
    matches = find_tracks(tracks, query, limit=30)

    if "seed_track_ids" not in st.session_state:
        st.session_state.seed_track_ids = []

    selected_id: str | None = None
    if matches.empty:
        st.warning("No matching tracks. Try another title or artist.")
    else:
        label_to_id = {
            f"{display_label(row)} · {row['track_id'][-5:]}": str(row["track_id"])
            for _, row in matches.iterrows()
        }
        selected_label = st.selectbox("Track", options=list(label_to_id))
        selected_id = label_to_id[selected_label]

    add_column, clear_column = st.columns(2)
    if add_column.button(
        "Add to profile",
        use_container_width=True,
        disabled=selected_id is None,
    ):
        if selected_id in st.session_state.seed_track_ids:
            st.toast("This track is already in your profile.")
        elif len(st.session_state.seed_track_ids) >= MAX_SEED_TRACKS:
            st.warning(f"Choose up to {MAX_SEED_TRACKS} seed tracks.")
        else:
            st.session_state.seed_track_ids.append(selected_id)
            st.rerun()

    if clear_column.button(
        "Clear profile",
        use_container_width=True,
        disabled=not st.session_state.seed_track_ids,
    ):
        st.session_state.seed_track_ids = []
        st.rerun()

    st.markdown(f"**Selected tracks ({len(st.session_state.seed_track_ids)}/{MAX_SEED_TRACKS})**")
    if not st.session_state.seed_track_ids:
        st.info("Add one to five tracks to create your playlist profile.")
    else:
        for seed_id in list(st.session_state.seed_track_ids):
            seed = tracks.loc[tracks["track_id"].eq(seed_id)].iloc[0]
            label_column, remove_column = st.columns([5, 1])
            label_column.caption(display_label(seed))
            if remove_column.button("×", key=f"remove-{seed_id}", help="Remove track"):
                st.session_state.seed_track_ids.remove(seed_id)
                st.rerun()

    count = st.slider("Number of recommendations", 5, 20, 10)
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
    recommend = st.button(
        "Build my playlist",
        type="primary",
        use_container_width=True,
        disabled=not st.session_state.seed_track_ids,
    )

with results_column:
    st.subheader("Your playlist")
    if recommend:
        recommendations = model.recommend_from_tracks(
            st.session_state.seed_track_ids,
            n_recommendations=count,
            popularity_bias=popularity_bias,
            same_genre_only=same_genre,
            diversity=diversity,
            max_tracks_per_artist=max_tracks_per_artist,
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
                  <div><span class="score">{row['similarity']:.0%} profile match</span>
                       · popularity {int(row['popularity'])}/100</div>
                  <div class="muted">{reason}</div>
                  <a href="{spotify_url}" target="_blank">Open in Spotify ↗</a>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Add a few tracks, adjust the controls, then build your playlist.")

with st.expander("How does it work?"):
    st.write(
        "The model averages the audio and genre vectors of your selected tracks into one "
        "taste profile. It finds candidates with cosine similarity, applies an optional "
        "popularity boost, and uses Maximum Marginal Relevance to keep the playlist diverse. "
        "Every result includes a short explanation."
    )
    st.caption(f"Using: {path.relative_to(PROJECT_ROOT)}")
