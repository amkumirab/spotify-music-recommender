# Local data and publication

Playlist Studio is designed for a local, single-user computer. Do not expose a
running instance to the public internet without adding authentication and
isolating each user's data.

| Data | Storage | Included in this repository? |
| --- | --- | --- |
| Access and refresh tokens | Session memory | No |
| OAuth state, verifier and authorization code | Short-lived process memory | No |
| Imported Liked Songs and match report | Session memory | No |
| Explicitly saved recommendation snapshots | `data/local/library.db` | No |
| Personal screenshots from local testing | `data/local/` | No |
| Public demo screenshots | `docs/images/` | Yes |
| Attributed public catalog sample and manifest | `data/sample/`, `data/catalog_manifest.json` | Yes |

Disconnect clears the connection, imported taste and current result. Explicitly
saved recommendation snapshots remain on the device. Restarting the app process
clears in-memory credentials. Local disconnection does not revoke Spotify-side
authorization; use Spotify's account Apps settings to revoke it.

Public screenshots use the labeled demo taste. They contain no personal account
name, Liked Songs export, Client ID, authorization URL, or token. Never replace
these images with a personal test screenshot without reviewing its full contents.

Environment files, SQLite files, private keys, raw downloads, reports and local
test artifacts are excluded by `.gitignore`. The example catalog contains public
music metadata, not anyone's private listening history. Dataset attribution and
license terms are documented in `data/DATASET.md`.
