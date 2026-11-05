"""Manual taste selection, separate from imported Liked Songs."""

import pandas as pd
import streamlit as st

from spotify_recommender.data import display_label, find_tracks


def render_manual_profile(tracks: pd.DataFrame, max_seeds: int = 5) -> None:
    query = st.text_input(
        "Search by song or artist", placeholder="Try: Coldplay", key="search_query"
    )
    matches = find_tracks(tracks, query, limit=30)
    selected_id = None
    if matches.empty:
        st.warning("No matching tracks. Try another title or artist.")
    else:
        labels = {
            f"{display_label(row)} · {row['track_id'][-5:]}": str(row["track_id"])
            for _, row in matches.iterrows()
        }
        selected_id = labels[st.selectbox("Track", options=list(labels))]
    add_column, clear_column = st.columns(2)
    if add_column.button(
        "Add to profile",
        key="add_seed",
        use_container_width=True,
        disabled=selected_id is None,
    ):
        if selected_id in st.session_state.seed_track_ids:
            st.toast("This track is already in your profile.")
        elif len(st.session_state.seed_track_ids) >= max_seeds:
            st.warning(f"Choose up to {max_seeds} seed tracks.")
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
    st.markdown(f"**Selected tracks ({len(st.session_state.seed_track_ids)}/{max_seeds})**")
    if not st.session_state.seed_track_ids:
        st.info("Add one to five tracks to create your playlist profile.")
    for seed_id in list(st.session_state.seed_track_ids):
        seed = tracks.loc[tracks["track_id"].eq(seed_id)].iloc[0]
        label_column, remove_column = st.columns([5, 1])
        label_column.caption(display_label(seed))
        if remove_column.button("×", key=f"remove-{seed_id}", help="Remove track"):
            st.session_state.seed_track_ids.remove(seed_id)
            st.rerun()
