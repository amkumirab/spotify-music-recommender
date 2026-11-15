# Private Spotify export

## Scope and acceptance criteria

- Preserve read-only authorization by default; opt-in adds only private playlist writes.
- Preview the current result and require confirmation tied to its name and ordered IDs.
- Validate a nonblank name of at most 100 characters and 1–100 unique track IDs.
- Create a new private playlist, append one ordered batch, and show its canonical link.
- Never change Liked Songs, existing playlists, or public playlists.
- Keep credentials, export results and duplicate protection in connection memory only.
- Reuse successful or uncertain outcomes for repeated identical exports in a connection.
- Never retry ambiguous writes. Preserve a known playlist link even if adding items fails.
- Keep local snapshots, downloads, offline discovery and read-only sync working unchanged.

## Failure semantics

Spotify does not provide an idempotency key for these writes. Creation and adding
items are two separate requests, not a transaction. A missing response is not
evidence of failure. The client serializes export calls and remembers an uncertain
outcome rather than blindly creating another playlist. Users must inspect Spotify
manually in this case. Restart/reconnect clears this protection; cross-session
deduplication and automatic repair are deliberately out of scope.

Token refresh happens before creation. An unsuccessful refresh or missing write
permission prevents the export without issuing a playlist write. API errors never
expose raw responses, authorization headers or credentials.

## Verification

Unit tests cover opt-in scope, private payloads, order/deduplication, invalid inputs,
token refresh, malformed responses and uncertain write outcomes. Streamlit AppTest
covers confirmation, permission upgrade, rerun persistence and error presentation.
These tests mock Spotify responses; they do not claim a live account export.
