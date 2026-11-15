"""Explicit, previewed writes to a connected Spotify account."""

import hashlib
import json

import streamlit as st

from spotify_recommender.spotify import SpotifyError


def render_spotify_export() -> None:
    playlist = st.session_state.get("playlist")
    if playlist is None or playlist.empty:
        return
    with st.expander("Save to Spotify", expanded=True):
        st.caption(
            "Creates a new private playlist in your connected account. "
            "Your Liked Songs and existing playlists are not changed."
        )
        client = st.session_state.get("spotify_client")
        if client is None or not getattr(client, "can_export", False):
            st.info(
                "Enable private playlist saving in the sidebar and finish the Spotify connection. "
                "Local saving and downloads still work without it."
            )
            return
        name = st.session_state.get("playlist_name", "").strip()
        ids = playlist["track_id"].astype(str).tolist()
        st.write(f"{len(ids)} tracks · Private · Order matches the Tracks tab above")
        with st.expander("Review tracks before saving"):
            st.dataframe(playlist[["track_name", "artists"]], hide_index=True)
        try:
            result = client.export_result(name, ids) if name else None
        except ValueError as error:
            st.warning(str(error))
            return
        # Changing the name or tracks invalidates consent to the previous intent.
        intent = hashlib.sha256(json.dumps([name, ids]).encode()).hexdigest()
        if st.session_state.get("spotify_confirmation_intent") != intent:
            st.session_state.confirm_spotify_export = False
            st.session_state.spotify_confirmation_intent = intent
        confirmed = st.checkbox(
            "Create this private playlist in my Spotify account",
            key="confirm_spotify_export",
            disabled=result is not None,
        )
        clicked = st.button(
            "Save private playlist to Spotify", key="save_spotify",
            disabled=not name or not confirmed or result is not None,
        )
        if not name:
            st.caption("Enter a playlist name above first.")
        if clicked:
            try:
                with st.spinner("Saving your private playlist on Spotify..."):
                    client.export_private_playlist(name, ids)
            except (ValueError, SpotifyError) as error:
                st.error(str(error))
            else:
                st.rerun()
        if result is not None:
            if result.status == "complete":
                st.success("Saved privately on Spotify. Repeated clicks will not create a copy.")
            else:
                st.warning(
                    "Check Spotify before doing anything else: the result could not be confirmed. "
                    "A playlist may have been created or only partly filled. "
                    "This save will not be retried automatically."
                )
            if result.url:
                st.link_button("Open playlist in Spotify", result.url)
        st.caption(
            "Duplicate protection lasts for this connection only. After reconnecting or "
            "restarting, check Spotify before saving the same playlist again."
        )
