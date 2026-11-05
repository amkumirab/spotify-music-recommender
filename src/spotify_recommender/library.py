"""Local, single-user playlist snapshots backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

from spotify_recommender.export import REQUIRED_COLUMNS


class PlaylistLibrary:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS playlists ("
                "id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL, "
                "track_count INTEGER NOT NULL, tracks TEXT NOT NULL, settings TEXT NOT NULL)"
            )

    def save(self, name: str, tracks: pd.DataFrame, settings: dict) -> str:
        name = name.strip()
        if not name or len(name) > 100:
            raise ValueError("Playlist name must contain 1 to 100 characters")
        if tracks.empty or not REQUIRED_COLUMNS.issubset(tracks.columns):
            raise ValueError("Save a non-empty playlist with the required track columns")
        playlist_id = uuid4().hex
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "INSERT INTO playlists VALUES (?, ?, ?, ?, ?, ?)",
                (
                    playlist_id,
                    name,
                    datetime.now(timezone.utc).isoformat(),
                    len(tracks),
                    tracks.to_json(orient="records"),
                    json.dumps(settings, allow_nan=False),
                ),
            )
        return playlist_id

    def list_playlists(self) -> list[dict]:
        with closing(sqlite3.connect(self.path)) as connection:
            connection.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT id, name, created_at, track_count FROM playlists "
                    "ORDER BY created_at DESC, id DESC"
                )
            ]

    def load(self, playlist_id: str) -> dict:
        with closing(sqlite3.connect(self.path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
            ).fetchone()
        if row is None:
            raise KeyError("Saved playlist not found")
        snapshot = dict(row)
        snapshot["tracks"] = pd.DataFrame(json.loads(snapshot["tracks"]))
        snapshot["settings"] = json.loads(snapshot["settings"])
        return snapshot

    def delete(self, playlist_id: str) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
