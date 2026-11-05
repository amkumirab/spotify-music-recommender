# Discovery from Liked Songs

## Goal

Connect a personal Spotify account, read Liked Songs with consent, and find songs
outside that library using a versioned offline catalog. New means not already
liked, rather than necessarily newly released. Release-year controls provide the
latter when release dates are available.

## Components and order

1. Catalog: merge a pinned real Kaggle chart snapshot with the existing audio
   catalog, retain source attribution, dates and a reproducible manifest.
2. Spotify: Authorization Code with PKCE and a loopback callback; read-only
   `user-library-read` scope, paginated saved tracks and token refresh.
3. Discovery: match by exact Spotify ID, then exact normalized title + primary
   artist for relinked versions. Report unmatched items; exclude every liked ID
   and known matching versions from recommendations. Choose up to 50 recent
   matched likes for the taste profile.
4. UI: connect/sync/disconnect, match report, discovery action, offline pasted
   track fallback, release-date filtering, download/share links, README gallery.

## Privacy and boundaries

Tokens, codes and raw liked-song responses stay in process/session memory, never
in caches, logs, SQLite, screenshots or Git. Callback listens only on 127.0.0.1,
expires after five minutes, validates state and accepts one authorization result.
Disconnect clears credentials and imported account data. API URLs are fixed;
pagination offsets are generated locally. Rate limits and access errors are
shown without leaking token/error payloads. No library writes are requested.
Snapshots retain generated recommendations, not tokens or the complete library.

Live login needs a user-owned Spotify app Client ID, registered redirect URI,
eligible account and authorized-user access. Offline samples exercise the UI
without pretending to be a connected account. Personal screenshots use demo data.

## Acceptance and verification

- Verified real, non-synthetic source with source and snapshot dates.
- Missing audio values are not invented for new songs.
- Sync exhausts pagination or fails explicitly; partial reads are not called complete.
- Known/unknown matches are visible and liked songs are excluded from discovery.
- Disconnect, invalid state, expiration, refresh, 403 and 429 have tests.
- Existing model calls, saved playlists, CSV and evaluation commands still work.
- Screenshot gallery contains actual rendered UI with no personal account data.

Run `python -m ruff check .`, `python -m pytest --cov=spotify_recommender`,
`python scripts/update_catalog.py`, and `python -m streamlit run app.py`.
