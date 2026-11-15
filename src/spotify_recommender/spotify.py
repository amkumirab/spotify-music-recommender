"""In-memory PKCE library access and opt-in private playlist export."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import secrets
import threading
import time
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

REDIRECT_URI = "http://127.0.0.1:8000/callback"


class SpotifyError(Exception):
    """An actionable error that never includes credentials or raw API payloads."""


@dataclass(frozen=True)
class PlaylistExport:
    status: str
    playlist_id: str | None = None

    @property
    def url(self) -> str | None:
        return (
            f"https://open.spotify.com/playlist/{self.playlist_id}"
            if self.playlist_id else None
        )


def _export_intent(name: str, track_ids: list[str]) -> tuple[str, str, list[str]]:
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise ValueError("Enter a playlist name between 1 and 100 characters.")
    if not isinstance(track_ids, (list, tuple)) or not all(
        isinstance(item, str) and re.fullmatch(r"[A-Za-z0-9]{22}", item)
        for item in track_ids
    ):
        raise ValueError("A playlist must contain valid Spotify track IDs.")
    ids = list(dict.fromkeys(track_ids))
    if not 1 <= len(ids) <= 100:
        raise ValueError("Save between 1 and 100 unique tracks at a time.")
    name = name.strip()
    key = hashlib.sha256(json.dumps([name, ids]).encode()).hexdigest()
    return key, name, ids


def request_json(request: Request) -> dict:
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 429:
            raise SpotifyError("Spotify rate limit reached. Wait and sync again later.") from None
        if error.code == 403:
            raise SpotifyError(
                "Spotify denied access. Check Premium eligibility and the app's authorized users."
            ) from None
        if error.code == 401:
            raise SpotifyError("Spotify session expired. Disconnect and sign in again.") from None
        raise SpotifyError(
            f"Spotify request failed (HTTP {error.code}). Try again later."
        ) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise SpotifyError(
            "Could not reach Spotify or read its response. Try again later."
        ) from None
    if not isinstance(payload, dict):
        raise SpotifyError("Unexpected Spotify response.")
    return payload


class LoginAttempt:
    """A short-lived loopback listener; authorization material is never persisted."""

    def __init__(
        self, client_id: str, port: int = 8000, *, allow_playlist_export: bool = False
    ) -> None:
        if not re.fullmatch(r"[a-fA-F0-9]{32}", client_id):
            raise ValueError("Enter the 32-character Client ID from Spotify Developer Dashboard.")
        self.client_id = client_id
        self.state = secrets.token_urlsafe(32)
        self.verifier = secrets.token_urlsafe(64)
        self.expires_at = time.time() + 300
        self.code: str | None = None
        self.error: str | None = None
        self._accepted = False
        self._closed = False
        self._lock = threading.Lock()
        attempt = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                valid = parsed.path == "/callback" and attempt.accept(parse_qs(parsed.query))
                self.send_response(200 if valid else 400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", "default-src 'none'")
                self.end_headers()
                self.wfile.write(
                    b"Return to Playlist Studio and click Finish connection."
                    if valid
                    else b"Invalid or expired sign-in. Start again in Playlist Studio."
                )

            def log_message(self, *_args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.redirect_uri = f"http://127.0.0.1:{self.server.server_port}/callback"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        self._timer = threading.Timer(300, self.close)
        self._timer.daemon = True
        self._timer.start()
        challenge = urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest())
        self.url = "https://accounts.spotify.com/authorize?" + urlencode(
            {
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "scope": "user-library-read" + (
                    " playlist-modify-private" if allow_playlist_export else ""
                ),
                "state": self.state,
                "code_challenge_method": "S256",
                "code_challenge": challenge.decode().rstrip("="),
            }
        )

    def accept(self, query: dict) -> bool:
        with self._lock:
            state = query.get("state", [""])[0]
            if (
                self._accepted
                or self._closed
                or time.time() > self.expires_at
                or len(state) > 200
                or not hmac.compare_digest(state.encode(), self.state.encode())
            ):
                return False
            code = query.get("code", [""])[0]
            if not code and "error" not in query:
                return False
            self._accepted = True
            self.code = code or None
            self.error = (
                "Spotify sign-in was declined. Start again to connect." if not code else None
            )
            return True

    def finish(self) -> SpotifyClient:
        if time.time() > self.expires_at:
            raise SpotifyError("Sign-in expired. Start again.")
        if self.error:
            raise SpotifyError(self.error)
        if not self.code:
            raise SpotifyError("Complete sign-in in the Spotify tab, then try again.")
        payload = request_json(
            Request(
                "https://accounts.spotify.com/api/token",
                data=urlencode(
                    {
                        "grant_type": "authorization_code",
                        "code": self.code,
                        "redirect_uri": self.redirect_uri,
                        "client_id": self.client_id,
                        "code_verifier": self.verifier,
                    }
                ).encode(),
            )
        )
        self.code = None
        return SpotifyClient(self.client_id, payload)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._timer.cancel()
        self.server.shutdown()
        self.server.server_close()
        self.code = None
        self.verifier = ""
        self.state = ""


class SpotifyClient:
    def __init__(self, client_id: str, token: dict) -> None:
        self.client_id = client_id
        self._exports: dict[str, PlaylistExport] = {}
        self._export_lock = threading.Lock()
        self._set_token(token)

    def _set_token(self, token: dict) -> None:
        if not isinstance(token.get("access_token"), str) or not token["access_token"]:
            raise SpotifyError("Spotify did not return a valid access token. Sign in again.")
        try:
            expires_in = float(token.get("expires_in", 3600))
            if not math.isfinite(expires_in) or expires_in <= 0:
                raise ValueError
        except (ValueError, TypeError):
            raise SpotifyError("Invalid Spotify token expiry. Sign in again.") from None
        self.access_token = token["access_token"]
        self.refresh_token = token.get("refresh_token", getattr(self, "refresh_token", None))
        if "scope" in token:
            scope = token["scope"]
            self.scopes = set(scope.split()) if isinstance(scope, str) else set()
        elif not hasattr(self, "scopes"):
            self.scopes = set()
        self.expires_at = time.time() + expires_in - 30

    @property
    def can_export(self) -> bool:
        return "playlist-modify-private" in self.scopes

    def _ensure_fresh_token(self) -> None:
        if time.time() >= self.expires_at:
            if not self.refresh_token:
                raise SpotifyError("Spotify session expired. Disconnect and sign in again.")
            self._set_token(
                request_json(
                    Request(
                        "https://accounts.spotify.com/api/token",
                        data=urlencode(
                            {
                                "grant_type": "refresh_token",
                                "client_id": self.client_id,
                                "refresh_token": self.refresh_token,
                            }
                        ).encode(),
                    )
                )
            )

    def get(self, path: str) -> dict:
        if not path.startswith("/me/tracks?"):
            raise ValueError("Only the saved-tracks endpoint is supported")
        self._ensure_fresh_token()
        return request_json(
            Request(
                "https://api.spotify.com/v1" + path,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
        )

    def export_result(self, name: str, track_ids: list[str]) -> PlaylistExport | None:
        key, _, _ = _export_intent(name, track_ids)
        return self._exports.get(key)

    def export_private_playlist(self, name: str, track_ids: list[str]) -> PlaylistExport:
        """Create once per connection and intent; never retry an ambiguous write."""
        key, name, ids = _export_intent(name, track_ids)
        with self._export_lock:
            if key in self._exports:
                return self._exports[key]
            self._ensure_fresh_token()
            if not self.can_export:
                raise SpotifyError("Enable private playlist permission and connect again first.")

            def post(path: str, payload: dict) -> dict:
                return request_json(Request(
                    "https://api.spotify.com/v1" + path,
                    data=json.dumps(payload).encode(),
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                ))

            playlist_id = None
            try:
                created = post("/me/playlists", {"name": name, "public": False})
                candidate = created.get("id")
                if not isinstance(candidate, str) or not re.fullmatch(
                    r"[A-Za-z0-9]{22}", candidate
                ):
                    raise SpotifyError("Unexpected playlist response.")
                playlist_id = candidate
                added = post(f"/playlists/{playlist_id}/items", {
                    "uris": [f"spotify:track:{item}" for item in ids],
                })
                if not isinstance(added.get("snapshot_id"), str) or not added["snapshot_id"]:
                    raise SpotifyError("Unexpected playlist update response.")
            except SpotifyError:
                result = PlaylistExport("unknown", playlist_id)
            else:
                result = PlaylistExport("complete", playlist_id)
            self._exports[key] = result
            return result

    def liked_songs(self) -> list[dict]:
        songs = []
        offset = 0
        while offset < 100_000:
            page = self.get(f"/me/tracks?limit=50&offset={offset}")
            items = page.get("items")
            total = page.get("total")
            if not isinstance(items, list) or not isinstance(total, int) or total < 0:
                raise SpotifyError("Unexpected Spotify library response.")
            for item in items:
                track = item.get("track") if isinstance(item, dict) else None
                if (
                    not isinstance(track, dict)
                    or not re.fullmatch(r"[A-Za-z0-9]{22}", str(track.get("id", "")))
                    or track.get("is_local")
                ):
                    continue
                artists = track.get("artists") or []
                if not isinstance(artists, list) or not all(isinstance(a, dict) for a in artists):
                    raise SpotifyError("Unexpected Spotify artist response.")
                songs.append(
                    {
                        "track_id": track["id"],
                        "track_name": str(track.get("name", "")),
                        "artists": ";".join(str(artist.get("name", "")) for artist in artists),
                        "added_at": str(item.get("added_at", "")),
                        "original_id": (track.get("linked_from") or {}).get("id", track["id"]),
                    }
                )
            offset += len(items)
            if page.get("next") is None:
                if offset < total:
                    raise SpotifyError("Spotify library response was incomplete. Sync again.")
                return songs
            if not items:
                raise SpotifyError("Spotify library response was incomplete. Sync again.")
        raise SpotifyError("Library exceeds the 100,000-item safety limit; sync was not completed.")
