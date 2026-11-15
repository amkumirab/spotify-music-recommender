import json
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlparse

import pytest

from spotify_recommender import spotify
from spotify_recommender.spotify import LoginAttempt, SpotifyClient, SpotifyError


def writer():
    return SpotifyClient("a" * 32, {
        "access_token": "test", "expires_in": 3600,
        "scope": "user-library-read playlist-modify-private",
    })


def test_export_permission_is_opt_in():
    attempt = LoginAttempt("a" * 32, port=0, allow_playlist_export=True)
    try:
        assert set(parse_qs(urlparse(attempt.url).query)["scope"][0].split()) == {
            "user-library-read", "playlist-modify-private"
        }
    finally:
        attempt.close()


def test_private_export_preserves_order_and_reuses_success(monkeypatch):
    requests = []
    def respond(request):
        requests.append(request)
        return {"id": "p" * 22} if len(requests) == 1 else {"snapshot_id": "saved"}
    monkeypatch.setattr(spotify, "request_json", respond)
    client = writer()
    ids = ["b" * 22, "a" * 22, "b" * 22]
    result = client.export_private_playlist("  Evening mix  ", ids)
    assert result.status == "complete"
    assert result.url == "https://open.spotify.com/playlist/" + "p" * 22
    assert json.loads(requests[0].data) == {"name": "Evening mix", "public": False}
    assert requests[0].full_url == "https://api.spotify.com/v1/me/playlists"
    assert requests[1].full_url.endswith("/playlists/" + "p" * 22 + "/items")
    assert json.loads(requests[1].data)["uris"] == ["spotify:track:" + i for i in ids[:2]]
    assert client.export_private_playlist("Evening mix", ids) == result
    assert len(requests) == 2


def test_unknown_create_outcome_is_not_retried(monkeypatch):
    calls = []
    def fail(request):
        calls.append(request)
        raise SpotifyError("Could not reach Spotify.")
    monkeypatch.setattr(spotify, "request_json", fail)
    client = writer()
    result = client.export_private_playlist("Mix", ["a" * 22])
    assert result.status == "unknown"
    assert result.url is None
    assert client.export_private_playlist("Mix", ["a" * 22]) == result
    assert len(calls) == 1


def test_unknown_add_outcome_keeps_playlist_link_without_repeating(monkeypatch):
    calls = []
    def respond(request):
        calls.append(request)
        if len(calls) == 1:
            return {"id": "p" * 22}
        raise SpotifyError("Spotify rate limit reached.")
    monkeypatch.setattr(spotify, "request_json", respond)
    client = writer()
    result = client.export_private_playlist("Mix", ["a" * 22])
    assert result.status == "unknown"
    assert result.url is not None
    assert client.export_private_playlist("Mix", ["a" * 22]) == result
    assert len(calls) == 2


def test_read_only_client_cannot_write(monkeypatch):
    monkeypatch.setattr(spotify, "request_json", lambda _: pytest.fail("Unexpected API call"))
    client = SpotifyClient("id", {"access_token": "test", "expires_in": 3600})
    with pytest.raises(SpotifyError, match="permission"):
        client.export_private_playlist("Mix", ["a" * 22])


@pytest.mark.parametrize("name, ids", [(" ", ["a" * 22]), ("Mix", []),
    ("Mix", ["invalid"]), ("Mix", "a" * 22), ("x" * 101, ["a" * 22]),
    ("Mix", [str(i).zfill(22) for i in range(101)])])
def test_invalid_export_never_reaches_spotify(monkeypatch, name, ids):
    monkeypatch.setattr(spotify, "request_json", lambda _: pytest.fail("Unexpected API call"))
    with pytest.raises(ValueError):
        writer().export_private_playlist(name, ids)


@pytest.mark.parametrize("created, added, expected_id", [
    ({"id": "https://bad.test"}, {}, None),
    ({}, {}, None),
    ({"id": "p" * 22}, {}, "p" * 22),
])
def test_malformed_responses_do_not_claim_success(monkeypatch, created, added, expected_id):
    responses = iter([created, added])
    monkeypatch.setattr(spotify, "request_json", lambda _: next(responses))
    client = writer()
    result = client.export_private_playlist("Mix", ["a" * 22])
    assert result.status == "unknown"
    assert result.playlist_id == expected_id
    assert client.export_result("Mix", ["a" * 22]) == result


@pytest.mark.parametrize("scope", [None, "user-library-read"])
def test_refresh_preserves_or_rechecks_write_permission(monkeypatch, scope):
    client = writer()
    client.expires_at = 0
    client.refresh_token = "refresh-test"
    calls = []

    def respond(request):
        calls.append(request)
        if len(calls) == 1:
            token = {"access_token": "fresh", "expires_in": 3600}
            if scope is not None:
                token["scope"] = scope
            return token
        return {"id": "p" * 22} if len(calls) == 2 else {"snapshot_id": "saved"}

    monkeypatch.setattr(spotify, "request_json", respond)
    if scope is None:
        assert client.export_private_playlist("Mix", ["a" * 22]).status == "complete"
        assert len(calls) == 3
        assert calls[1].get_header("Authorization") == "Bearer fresh"
    else:
        with pytest.raises(SpotifyError, match="permission"):
            client.export_private_playlist("Mix", ["a" * 22])
        assert len(calls) == 1


def test_concurrent_export_only_creates_once(monkeypatch):
    calls = []

    def respond(request):
        calls.append(request)
        return {"id": "p" * 22} if len(calls) == 1 else {"snapshot_id": "saved"}

    monkeypatch.setattr(spotify, "request_json", respond)
    client = writer()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _: client.export_private_playlist("Mix", ["a" * 22]), [0, 1]
        ))
    assert results[0] == results[1]
    assert len(calls) == 2
