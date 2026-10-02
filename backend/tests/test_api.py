from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.health_check import HealthCheck


def post(client, url):
    return client.post("/api/check", json={"url": url})


def ok(request):
    return httpx.Response(200)


# --- /health ---------------------------------------------------------------

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- POST /api/check -------------------------------------------------------

def test_check_success_is_saved(client, mock_http):
    mock_http(ok)
    response = post(client, "https://good.example/")
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["status"] == "up"
    assert body["status_code"] == 200
    assert body["error_message"] is None
    assert body["response_time_ms"] >= 0
    assert body["checked_at"].endswith("Z")
    assert client.get("/api/checks/1").json() == body


def test_check_http_error_is_saved_as_down(client, mock_http):
    mock_http(lambda request: httpx.Response(404))
    response = post(client, "https://good.example/missing")
    assert response.status_code == 201
    body = response.json()
    assert (body["status"], body["status_code"], body["error_message"]) == ("down", 404, "HTTP 404")


def test_check_timeout_is_saved_as_down(client, mock_http):
    def handler(request):
        raise httpx.ConnectTimeout("internal detail")

    mock_http(handler)
    response = post(client, "https://good.example/")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "down"
    assert body["status_code"] is None
    assert body["response_time_ms"] is None
    assert body["error_message"] == "Request timed out"
    assert "internal detail" not in response.text


def test_check_connection_failure_is_saved_as_down(client, mock_http):
    def handler(request):
        raise httpx.ConnectError("internal detail")

    mock_http(handler)
    body = post(client, "https://good.example/").json()
    assert body["status"] == "down"
    assert body["error_message"] == "Could not connect to host"


def test_check_unresolvable_host_is_saved_as_down(client):
    response = post(client, "http://nonexistent.invalid/")
    assert response.status_code == 201
    assert response.json()["error_message"] == "Could not resolve host"


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1", "http://localhost/health", "http://169.254.169.254/", "http://internal.example/"],
)
def test_check_blocked_destination_returns_400_and_is_not_saved(client, url):
    response = post(client, url)
    assert response.status_code == 400
    assert response.json() == {"detail": "URL destination is not allowed"}
    assert client.get("/api/checks").json()["total"] == 0


@pytest.mark.parametrize(
    "url", ["https://user:secret@good.example/", "https://token@good.example/?x=1"]
)
def test_check_url_with_credentials_is_rejected_and_not_stored(client, url):
    response = post(client, url)
    assert response.status_code == 400
    assert response.json() == {"detail": "URLs containing a username or password are not allowed"}
    assert "secret" not in response.text
    assert client.get("/api/checks").json()["total"] == 0


@pytest.mark.parametrize("url", ["ftp://good.example", "not-a-url", "", "javascript:alert(1)"])
def test_check_invalid_url_returns_422(client, url):
    assert post(client, url).status_code == 422
    assert client.get("/api/checks").json()["total"] == 0


def test_check_missing_url_returns_422(client):
    assert client.post("/api/check", json={}).status_code == 422


def test_unexpected_error_returns_generic_500(client, monkeypatch):
    def boom(url):
        raise RuntimeError("secret-internal-detail")

    monkeypatch.setattr("app.api.checks.perform_check", boom)
    with TestClient(app, raise_server_exceptions=False) as quiet_client:
        response = quiet_client.post("/api/check", json={"url": "https://good.example/"})
    assert response.status_code == 500
    assert "secret" not in response.text
    assert "Traceback" not in response.text


# --- GET /api/checks -------------------------------------------------------

def make_checks(client, mock_http, count):
    mock_http(ok)
    for i in range(count):
        assert post(client, f"https://good.example/{i}").status_code == 201


def test_history_empty(client):
    assert client.get("/api/checks").json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_history_is_newest_first(client, mock_http):
    make_checks(client, mock_http, 3)
    body = client.get("/api/checks").json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [3, 2, 1]


def test_history_pagination(client, mock_http):
    make_checks(client, mock_http, 3)
    ids = lambda page: [i["id"] for i in client.get(f"/api/checks?page={page}&page_size=2").json()["items"]]
    assert ids(1) == [3, 2]
    assert ids(2) == [1]
    assert ids(3) == []  # past the end: empty, not an error


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=101", "page=abc"])
def test_history_rejects_invalid_paging(client, query):
    assert client.get(f"/api/checks?{query}").status_code == 422


# --- GET /api/checks/{id} --------------------------------------------------

def test_get_check_not_found(client):
    response = client.get("/api/checks/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Check not found"}


def test_get_check_with_non_integer_id(client):
    assert client.get("/api/checks/abc").status_code == 422


# --- GET /api/stats --------------------------------------------------------

def test_stats_empty(client):
    assert client.get("/api/stats").json() == {
        "total_checks": 0,
        "successful_checks": 0,
        "failed_checks": 0,
        "average_response_time_ms": None,
    }


def test_stats_counts_and_average_are_exact(client, db_session):
    now = datetime(2026, 1, 1, 12, 0, 0)
    db_session.add_all(
        [
            HealthCheck(url="https://a.example/", status="up", status_code=200, response_time_ms=100.0, checked_at=now),
            HealthCheck(url="https://b.example/", status="down", status_code=500, response_time_ms=200.0, error_message="HTTP 500", checked_at=now),
            HealthCheck(url="https://c.example/", status="down", status_code=None, response_time_ms=None, error_message="Request timed out", checked_at=now),
        ]
    )
    db_session.commit()
    # The average ignores the check that never got a response (NULL), so (100 + 200) / 2.
    assert client.get("/api/stats").json() == {
        "total_checks": 3,
        "successful_checks": 1,
        "failed_checks": 2,
        "average_response_time_ms": 150.0,
    }


def test_stats_with_only_timeouts_has_no_average(client, mock_http):
    def handler(request):
        raise httpx.ReadTimeout("x")

    mock_http(handler)
    post(client, "https://good.example/")
    body = client.get("/api/stats").json()
    assert (body["total_checks"], body["failed_checks"]) == (1, 1)
    assert body["average_response_time_ms"] is None


# --- CORS ------------------------------------------------------------------

PREFLIGHT = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}


def test_cors_allows_frontend_origin(client):
    response = client.options("/api/check", headers={"Origin": "http://localhost:5173", **PREFLIGHT})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unknown_origin(client):
    response = client.options("/api/check", headers={"Origin": "http://evil.example", **PREFLIGHT})
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
