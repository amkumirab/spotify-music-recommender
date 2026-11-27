# Recommendation feedback

## Behavior

- Rate recommendations with More Like This or Less Like This. Store one explicit
  rating per track locally and let the listener undo it, even after restarting.
- Apply a small, capped similarity adjustment on the next build. Filters,
  imported-like exclusions and diversity constraints still apply. The current
  playlist stays unchanged and the profile-match percentage remains the seed
  similarity. With feedback disabled or absent, results stay unchanged.
- No Spotify writes, permissions, new dependencies, or model training.

## Implementation and checks

SQLite stores track IDs and rating directions in the existing local library.
Use parameterized SQL, stable ordering, and native Streamlit widgets. Put
storage and ranking logic in the recommender package and test each independently
before exercising the complete flow with Streamlit AppTest. Tests use temporary
databases; never inspect or modify the listener's real data during verification.

Run `python -m pytest` and `ruff check .`. Use `streamlit run app.py` to
preview the English UI locally.

The ranker averages the catalog feature vectors for each rating direction. It
adds up to 0.15 for positive cosine similarity to the "more" profile and subtracts
up to 0.15 for positive similarity to the "less" profile. These adjustments apply
to eligible candidates before the shortlist and are included in their ranking
scores. A rated track outside the current catalog is ignored until it is
available again. The displayed match percentage remains based on the seed profile.

To demo the effect without a Spotify account, select **Try a demo taste** and
build a playlist. Rate the first track **Less Like This** and build again.
Turn off **Use my feedback** and build a third time with the same settings to
compare with the baseline.
