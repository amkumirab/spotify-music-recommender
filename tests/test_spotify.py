import hashlib
from base64 import urlsafe_b64encode
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

import pytest

from spotify_recommender import spotify
from spotify_recommender.spotify import LoginAttempt, SpotifyClient, SpotifyError


def test_pkce_uses_read_only_scope_and_rejects_wrong_state():
    attempt = LoginAttempt("a" * 32, port=0)
    try:
        query = parse_qs(urlparse(attempt.url).query)
        expected = urlsafe_b64encode(hashlib.sha256(attempt.verifier.encode()).digest())
        assert query["code_challenge"] == [expected.decode().rstrip("=")]
        assert query["scope"] == ["user-library-read"]
        assert not attempt.accept({"state": ["wrong"], "code": ["secret-code"]})
        assert attempt.code is None
        assert attempt.accept({"state": [attempt.state], "code": ["valid-code"]})
        assert not attempt.accept({"state": [attempt.state], "code": ["replay"]})
    finally:
        attempt.close()


def test_expired_login_cannot_accept_code():
    attempt = LoginAttempt("a" * 32, port=0)
    try:
        attempt.expires_at = 0
        assert not attempt.accept({"state": [attempt.state], "code": ["expired"]})
    finally:
        attempt.close()


def test_liked_songs_are_paginated_and_unavailable_tracks_skipped(monkeypatch):
    client = SpotifyClient("a" * 32, {"access_token": "test", "expires_in": 3600})
    calls = []

    def page(path):
        calls.append(path)
        if "offset=0" in path:
            return {
                "items": [
                    {"track": None},
                    {"track": {"id": "b" * 22, "name": "Song", "artists": [{"name": "Artist"}]}},
                ],
                "total": 3,
                "next": "do-not-follow-external-url",
            }
        return {
            "items": [
                {"track": {"id": "c" * 22, "name": "Song 2", "artists": [{"name": "Artist 2"}]}}
            ],
            "total": 3,
            "next": None,
        }

    monkeypatch.setattr(client, "get", page)
    assert len(client.liked_songs()) == 2
    assert "offset=2" in calls[1]


def test_empty_page_does_not_silently_complete(monkeypatch):
    client = SpotifyClient("a" * 32, {"access_token": "test", "expires_in": 3600})
    monkeypatch.setattr(client, "get", lambda _: {"items": [], "total": 5, "next": "more"})
    with pytest.raises(SpotifyError, match="incomplete"):
        client.liked_songs()


@pytest.mark.parametrize(
    "status, message", [(403, "denied"), (429, "rate limit"), (401, "expired")]
)
def test_http_errors_never_expose_credentials(monkeypatch, status, message):
    def fail(*args, **kwargs):
        raise HTTPError("https://api.spotify.com/v1/me/tracks", status, "secret-token", {}, None)

    monkeypatch.setattr(spotify, "urlopen", fail)
    with pytest.raises(SpotifyError, match=message) as error:
        spotify.request_json(Request("https://api.spotify.com/v1/me/tracks"))
    assert "secret-token" not in str(error.value)


def test_expiring_token_refreshes_without_client_secret(monkeypatch):
    client = SpotifyClient(
        "a" * 32, {"access_token": "old", "refresh_token": "refresh-test", "expires_in": 1}
    )
    requests = []

    def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return {"access_token": "new", "expires_in": 3600}
        return {"items": [], "next": None, "total": 0}

    monkeypatch.setattr(spotify, "request_json", respond)
    assert client.liked_songs() == []
    assert "client_secret" not in requests[0].data.decode()
    assert requests[1].get_header("Authorization") == "Bearer new"
    assert client.refresh_token == "refresh-test"


def test_real_loopback_callback_and_code_exchange(monkeypatch):
    attempt = LoginAttempt("a" * 32, port=0)
    try:
        url = attempt.redirect_uri + "?state=" + attempt.state + "&code=local-test"
        with urlopen(url, timeout=5) as response:
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
        captured = []

        def exchange(request):
            captured.append(parse_qs(request.data.decode()))
            return {"access_token": "access-test", "expires_in": 3600}

        monkeypatch.setattr(spotify, "request_json", exchange)
        assert attempt.finish().access_token == "access-test"
        assert captured[0]["code_verifier"] == [attempt.verifier]
    finally:
        attempt.close()
    assert attempt.code is None
    assert attempt.verifier == ""


def test_login_error_states():
    with pytest.raises(ValueError):
        LoginAttempt("not-a-client-id")
    attempt = LoginAttempt("a" * 32, port=0)
    try:
        with pytest.raises(SpotifyError, match="Complete sign-in"):
            attempt.finish()
        assert attempt.accept({"state": [attempt.state], "error": ["access_denied"]})
        with pytest.raises(SpotifyError, match="declined"):
            attempt.finish()
        attempt.expires_at = 0
        with pytest.raises(SpotifyError, match="expired"):
            attempt.finish()
    finally:
        attempt.close()


def test_invalid_or_expired_tokens():
    with pytest.raises(SpotifyError, match="valid access token"):
        SpotifyClient("id", {})
    with pytest.raises(SpotifyError, match="expiry"):
        SpotifyClient("id", {"access_token": "test", "expires_in": "bad"})
    client = SpotifyClient("id", {"access_token": "test", "expires_in": 1})
    with pytest.raises(SpotifyError, match="expired"):
        client.get("/me/tracks?limit=50")
    with pytest.raises(ValueError):
        client.get("https://evil.test")
