"""Playlist presentation and local library controls."""

from __future__ import annotations

import sqlite3
from html import escape

import pandas as pd
import streamlit as st

from spotify_recommender.export import build_playlist_export
from spotify_recommender.library import PlaylistLibrary


def render_playlist(tracks: pd.DataFrame, settings: dict) -> None:
    playlist = st.session_state.playlist
    if playlist is None:
        st.info("Add a few tracks, adjust the controls, then build your playlist.")
        return
    if st.session_state.playlist_settings != settings:
        st.info(
            "Showing your last playlist. Build again to apply the current profile and controls."
        )
    if playlist.empty:
        st.warning(
            "No tracks remain. Widen the audio filters or restore hidden tracks and build again."
        )
        return
    metrics = st.columns(3)
    metrics[0].metric("Playlist tracks", len(playlist))
    metrics[1].metric("Profile match", f"{playlist['similarity'].mean():.0%}")
    metrics[2].metric("Primary artists", playlist["artists"].str.split(";").str[0].nunique())
    st.download_button(
        "Download playlist as CSV",
        data=build_playlist_export(playlist).to_csv(index=False).encode("utf-8-sig"),
        file_name="spotify_playlist.csv",
        mime="text/csv",
        use_container_width=True,
    )
    with st.expander("Take these songs to Spotify"):
        st.caption(
            "Copy the URI list for a playlist importer, or open individual songs above. "
            "Bulk paste support varies between Spotify Desktop versions. "
            "This app does not write to your Spotify account."
        )
        uri_text = "\n".join("spotify:track:" + str(track_id) for track_id in playlist["track_id"])
        st.code(uri_text, language=None)
        st.download_button(
            "Download Spotify URIs", uri_text, file_name="spotify_tracks.txt", mime="text/plain"
        )
    songs_tab, analysis_tab = st.tabs(["Tracks", "Sound profile"])
    with songs_tab:
        for rank, (_, row) in enumerate(playlist.iterrows(), start=1):
            with st.container(border=True):
                st.markdown(f"**{rank}. {escape(str(row['track_name']))}**", unsafe_allow_html=True)
                st.text(f"{row['artists']} · {row['track_genre']}")
                st.caption(
                    f"{row['similarity']:.0%} profile match · popularity {row['popularity']}/100"
                )
                st.text(str(row["reason"]))
                metadata = tracks.loc[tracks["track_id"].eq(row["track_id"])]
                if not metadata.empty and "release_year" in metadata:
                    year = metadata.iloc[0]["release_year"]
                    if pd.notna(year):
                        st.caption(f"Released {int(year)}")
                link_column, hide_column = st.columns([2, 1])
                link_column.link_button(
                    "Open in Spotify", f"https://open.spotify.com/track/{row['track_id']}"
                )
                if hide_column.button("Hide track", key=f"hide-{row['track_id']}"):
                    st.session_state.excluded_track_ids.append(str(row["track_id"]))
                    st.session_state.playlist = playlist[
                        playlist["track_id"].ne(row["track_id"])
                    ].reset_index(drop=True)
                    st.rerun()
    with analysis_tab:
        features = ["energy", "valence", "danceability", "acousticness", "instrumentalness"]
        selected = tracks[tracks["track_id"].isin(playlist["track_id"])]
        seeds = tracks[tracks["track_id"].isin(st.session_state.playlist_settings["seeds"])]
        if not selected.empty:
            comparison = pd.DataFrame({"Playlist": selected[features].mean()})
            if not seeds.empty:
                comparison["Seed profile"] = seeds[features].mean()
            chart_data = (
                comparison.rename_axis("Feature")
                .reset_index()
                .melt(id_vars="Feature", var_name="Profile", value_name="Value")
            )
            st.vega_lite_chart(
                chart_data,
                {
                    "mark": "bar",
                    "encoding": {
                        "x": {
                            "field": "Value",
                            "type": "quantitative",
                            "scale": {"domain": [0, 1]},
                        },
                        "y": {"field": "Feature", "type": "nominal"},
                        "yOffset": {"field": "Profile"},
                        "color": {"field": "Profile", "type": "nominal"},
                    },
                },
                use_container_width=True,
            )
            st.caption("Audio features range from 0 to 1. Valence describes musical positivity.")
            st.metric("Average tempo", f"{selected['tempo'].mean():.0f} BPM")
            st.bar_chart(playlist["track_genre"].value_counts().rename("Tracks"))
        else:
            st.info("Audio data for this saved playlist is unavailable in the current dataset.")
    st.text_input("Playlist name", max_chars=100, key="playlist_name")


def render_library(path: str) -> None:
    try:
        library = PlaylistLibrary(path)
        if st.button(
            "Save playlist locally",
            key="save_playlist",
            disabled=st.session_state.playlist is None or st.session_state.playlist.empty,
        ):
            try:
                library.save(
                    st.session_state.get("playlist_name", ""),
                    st.session_state.playlist,
                    st.session_state.playlist_settings,
                )
                st.success("Saved on this device.")
            except ValueError as error:
                st.warning(str(error))
        with st.expander("Saved playlists", expanded=False):
            snapshots = library.list_playlists()
            if not snapshots:
                st.caption("Save a named playlist to reopen it after restarting the app.")
                return
            by_id = {item["id"]: item for item in snapshots}
            selected = st.selectbox(
                "Saved playlist",
                list(by_id),
                format_func=lambda key: (
                    f"{by_id[key]['name']} · {by_id[key]['track_count']} tracks "
                    f"· {by_id[key]['created_at'][:16]} UTC"
                ),
            )
            if st.button("Open saved playlist", key="open_saved"):
                snapshot = library.load(selected)
                st.session_state.playlist = snapshot["tracks"]
                st.session_state.playlist_settings = snapshot["settings"]
                st.rerun()
            st.caption(
                "Local snapshots only. This does not create a playlist in your Spotify account."
            )
    except (sqlite3.Error, OSError) as error:
        st.error(f"Local library unavailable: {error}")
