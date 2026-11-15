"""Account connection and catalog coverage, with an explicit offline fallback."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from spotify_recommender.discovery import match_library, parse_track_links
from spotify_recommender.spotify import REDIRECT_URI, LoginAttempt, SpotifyError


def _import_likes(likes: list[dict], tracks: pd.DataFrame, source: str) -> None:
    st.session_state.library_report = match_library(likes, tracks)
    st.session_state.library_source = source
    st.session_state.profile_source = "My imported likes"


def _start_connection(client_id: str, allow_export: bool = False) -> None:
    old = st.session_state.pop("spotify_login", None)
    if old is not None:
        old.close()
    try:
        st.session_state.spotify_login = (
            LoginAttempt(client_id.strip(), allow_playlist_export=True)
            if allow_export else LoginAttempt(client_id.strip())
        )
    except (ValueError, OSError) as error:
        st.error(
            str(error) if isinstance(error, ValueError)
            else "Port 8000 is busy. Close other connection attempts."
        )


def render_account(tracks: pd.DataFrame) -> None:
    with st.sidebar:
        st.header("Your Spotify library")
        client = st.session_state.get("spotify_client")
        if client is None:
            st.caption("Connect once, sync your Liked Songs, discover tracks outside your library.")
            with st.expander("Connect Spotify", expanded=False):
                st.markdown(
                    "1. Create an app in [Spotify Developer Dashboard]"
                    "(https://developer.spotify.com/dashboard).\n"
                    "2. Register this exact redirect URI:"
                )
                st.code(REDIRECT_URI, language=None)
                st.caption(
                    "Development access requires an eligible Premium account and an authorized "
                    "user in the app settings. This connection is for local desktop use."
                )
                client_id = st.text_input(
                    "Client ID (public)",
                    value=os.environ.get("SPOTIFY_CLIENT_ID", ""),
                    key="spotify_client_id",
                )
                allow_export = st.checkbox(
                    "Allow saving private playlists", key="allow_spotify_export",
                    help="Optional playlist-modify-private permission. No public playlists.",
                )
                if st.button("Start Spotify connection", key="start_spotify"):
                    _start_connection(client_id, allow_export)
                st.caption(
                    "Read-only by default. Passwords stay on Spotify. Tokens stay in this session."
                )
        else:
            st.success(
                "Spotify connected · private playlist saving enabled"
                if getattr(client, "can_export", False) else "Spotify connected · read-only"
            )
            if not getattr(client, "can_export", False):
                st.caption("Saving to Spotify needs optional private playlist permission.")
                if st.button("Enable private playlist saving", key="enable_spotify_export"):
                    _start_connection(getattr(client, "client_id", ""), True)
            if st.button("Sync Liked Songs", key="sync_likes", type="primary"):
                try:
                    with st.spinner("Reading your library and matching the catalog..."):
                        _import_likes(client.liked_songs(), tracks, "Spotify Liked Songs")
                except SpotifyError as error:
                    st.error(str(error))
            if st.button("Disconnect and clear imported likes", key="disconnect_spotify"):
                attempt = st.session_state.pop("spotify_login", None)
                if attempt is not None:
                    attempt.close()
                for key in ("spotify_client", "library_report", "library_source"):
                    st.session_state.pop(key, None)
                st.session_state.playlist = None
                st.session_state.playlist_settings = {}
                st.session_state.profile_source = "Selected tracks"
                st.rerun()
        attempt = st.session_state.get("spotify_login")
        if attempt is not None:
            st.link_button("Sign in on Spotify", attempt.url)
            if st.button("Finish connection", key="finish_spotify"):
                try:
                    st.session_state.spotify_client = attempt.finish()
                except SpotifyError as error:
                    st.error(str(error))
                else:
                    attempt.close()
                    del st.session_state.spotify_login
                    st.rerun()
        with st.expander("No account setup? Paste track links"):
            st.caption(
                "In Spotify Desktop, select tracks in Liked Songs and copy. Paste their track "
                "URLs or URIs below. Playlist URLs alone do not contain the tracks."
            )
            text = st.text_area("Spotify track links", key="import_links", height=110)
            if st.button("Use these tracks as my taste", key="import_taste"):
                try:
                    ids = parse_track_links(text)
                    if not ids:
                        raise ValueError("Paste Spotify track links or spotify:track: URIs.")
                    _import_likes(
                        [{"track_id": track_id} for track_id in ids], tracks, "Pasted tracks"
                    )
                except ValueError as error:
                    st.warning(str(error))
            if st.button("Try a demo taste", key="demo_taste"):
                demo = (
                    tracks[
                        tracks["track_name"]
                        .str.casefold()
                        .isin(
                            {
                                "espresso",
                                "birds of a feather",
                                "beautiful things",
                                "blinding lights",
                                "die with a smile",
                            }
                        )
                    ]
                    .drop_duplicates("track_name")
                    .head(5)
                )
                if demo.empty:
                    demo = tracks.head(5)
                _import_likes(
                    demo.to_dict("records"), tracks, "Demo taste · not a connected account"
                )
        report = st.session_state.get("library_report")
        if report is not None:
            st.divider()
            st.caption(st.session_state.library_source)
            a, b = st.columns(2)
            a.metric("Matched likes", report["matched"])
            b.metric("Not in catalog", report["unmatched"])
            st.caption(
                f"Taste profile uses up to {len(report['seed_ids'])} recent matched songs. "
                "All imported IDs and matching recording versions are excluded from discovery."
            )
            if report["unmatched"]:
                st.warning(
                    "Some likes have no audio data in this catalog and cannot shape the profile."
                )
                with st.expander("Unmatched songs"):
                    st.dataframe(
                        pd.DataFrame(report["missing"]).reindex(
                            columns=["track_name", "artists", "track_id"]
                        ),
                        hide_index=True,
                        use_container_width=True,
                    )
            with st.expander("Songs shaping your profile"):
                st.dataframe(
                    tracks[tracks["track_id"].isin(report["seed_ids"])][["track_name", "artists"]],
                    hide_index=True,
                    use_container_width=True,
                )
            if st.button("Clear imported taste", key="clear_taste"):
                st.session_state.pop("library_report", None)
                st.session_state.pop("library_source", None)
                st.session_state.profile_source = "Selected tracks"
                st.rerun()
