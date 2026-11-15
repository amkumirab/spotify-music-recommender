# Connect Liked Songs

The account connection uses Spotify Authorization Code with PKCE. It reads your
library by default; it never asks for your Spotify password or a Client Secret.
Optional private playlist saving requires separate permission and explicit confirmation.

## One-time setup

1. Open [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   and create a personal app with Web API access.
2. Register this exact redirect URI in the app settings:
   `http://127.0.0.1:8000/callback`.
3. Follow Spotify's current [development-mode eligibility rules](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).
   The app owner needs an eligible Premium account. Add the listening account
   to the app's authorized-user list when required.
4. Copy the public **Client ID**. Do not use the Client Secret.
5. Run Playlist Studio, expand **Connect Spotify** in the sidebar and paste the
   Client ID. Alternatively set the `SPOTIFY_CLIENT_ID` environment variable.
6. Click **Start Spotify connection**, open **Sign in on Spotify** and approve
   the read-only library scope on Spotify's own page.
7. When the callback page says to return, go back and click **Finish connection**.
8. Click **Sync Liked Songs**, then **Discover new favourites**.

## Optional private playlist saving

Leave **Allow saving private playlists** unchecked for read-only access. To save
recommendations directly, check it before connecting, or choose **Enable private
playlist saving** on an existing connection. Complete sign-in again and click
**Finish connection**. This requests `playlist-modify-private` in addition to
`user-library-read`; no public-playlist permission is requested.

Build recommendations, enter a playlist name, review the tracks under **Save to
Spotify**, and confirm creation. Only clicking **Save private playlist to Spotify**
writes to your account. The new playlist is private and follows the displayed order.
Liked Songs and existing playlists are not modified.

The integration uses Spotify's [Create Playlist](https://developer.spotify.com/documentation/web-api/reference/create-playlist)
and [Add Items](https://developer.spotify.com/documentation/web-api/reference/add-items-to-playlist)
endpoints. At most 100 unique tracks are sent in one batch. Repeated clicks reuse
the saved result within the same connection. If the result is uncertain, check
Spotify manually before reconnecting or trying a different name. Automatic retries
could create an empty/duplicate playlist or add tracks twice, so writes are not retried.

Both the Streamlit app and the authorization browser must run on the same
computer. Port 8000 must be free. A sign-in attempt expires after five minutes;
start again if it expires. The connection is intentionally local and single-user.

## What shapes your recommendations

The app reads all pages of Liked Songs (up to a 100,000-item safety limit).
Unavailable/local items are skipped. It matches exact Spotify IDs, linked IDs,
and exact normalized title plus primary artist. It uses up to 50 recently saved,
matched songs as the audio taste profile. All imported IDs and known matching
versions are excluded, including older likes not used in the taste profile.

**New** means not already saved in the imported library. Enable **Only recent
releases** for a release-year constraint. Unmatched songs are reported and do not
influence the model; this catalog does not contain every Spotify song. Exact
metadata matching cannot identify every remix, translation, or alternate recording.

Spotify's [Audio Features restrictions](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)
mean new apps cannot simply fetch missing audio for every unknown song. This app
does not pretend that metadata-only matches have measured audio features.

## Privacy and troubleshooting

Authorization tokens and imported library data stay in session memory; they are
not written to the local playlist database, logs or Git. **Disconnect and clear
imported likes** clears the connection, imported taste and current result. Saved
playlist snapshots you explicitly created remain on the device. Restarting the
app process also clears the connection. Disconnecting locally does not revoke
the app at Spotify; revoke it from your Spotify account's Apps page if desired.

- **403:** check Premium eligibility, authorized users and app access.
- **429:** wait before syncing again; the app does not repeatedly retry.
- **Expired session:** refresh is automatic when possible; reconnect otherwise.
- **Few matches:** install the full merged catalog or paste other familiar songs.

**No developer app yet?** Paste copied track links in the sidebar or choose
**Try a demo taste**. The demo is explicitly labeled and uses public catalog songs.
It is not a simulated connected account. Screenshots in this repository use only
that demo and contain no personal listening history or credentials.

CSV and Spotify URI downloads remain available without write permission.
Individual Spotify links open the actual tracks. Bulk URI paste varies by Spotify
Desktop version; the optional private export avoids that manual step.
