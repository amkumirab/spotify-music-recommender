# Playlist Studio

## Scope and build order

1. `discovery`: optional audio ranges and exclusions, applied before candidate retrieval.
2. `library`: local SQLite snapshots of playlists; independent of the recommender.
3. `studio`: persistent session results, feedback, comparison charts, saved playlist access.

The application stays local and uses the existing Python/Streamlit stack. No
Spotify credentials or new runtime dependencies are required for offline use. Library data belongs
in `data/local/` and is excluded from Git. This is a single-user desktop app;
deployments must isolate each user's storage before enabling shared hosting.

Optional account integration is covered by [Liked Songs discovery](spotify-discovery.md)
and [private Spotify export](spotify-export.md). Local snapshots do not write to Spotify.

## Acceptance criteria

- Optional energy, valence and tempo ranges are inclusive and validated.
- Excluded IDs and out-of-range tracks never enter the candidate pool.
- Existing recommendation calls continue to work without new arguments.
- Empty pools return the normal result schema without exceptions.
- Searching, downloading and editing controls retain the last generated playlist.
- Pending control changes are labeled and applied on the next build.
- Hide feedback removes a track and excludes it from future builds in the session.
- Named snapshots survive process restarts, preserve order and use parameterized SQL.
- Saved playlists can be reopened and exported without regenerating recommendations.
- Audio comparisons use the dataset's normalized 0–1 features; tempo stays in BPM.

## Implementation and verification

Model logic lives in `src/spotify_recommender/model.py`, storage in `library.py`,
presentation helpers in `studio.py`, and orchestration in `app.py`. Tests live in
`tests/` and follow the existing pytest conventions, for example:

```python
result = model.recommend_from_tracks(["a"], excluded_track_ids=["b"])
assert "b" not in set(result["track_id"])
```

Commands: `python -m ruff check .`,
`python -m pytest --cov=spotify_recommender --cov-report=term-missing`,
`python -m streamlit run app.py`.

Verification includes unit tests for filtering and storage, Streamlit AppTest
flows for state persistence and feedback, a full-dataset smoke run, and browser
inspection when browser tooling is available. Preserve existing tests and APIs;
do not commit local databases, raw datasets or credentials.
