import httpx
import pytest

from app.services.checker import perform_check
from app.services.ssrf import UnsafeURLError

URL = "https://good.example/"


def check(handler, url=URL):
    return perform_check(url, transport=httpx.MockTransport(handler))


def test_success_is_up():
    outcome = check(lambda request: httpx.Response(200))
    assert outcome.status == "up"
    assert outcome.status_code == 200
    assert outcome.error_message is None
    assert outcome.response_time_ms is not None and outcome.response_time_ms >= 0


@pytest.mark.parametrize("code", [404, 500, 503])
def test_http_error_status_is_down(code):
    outcome = check(lambda request: httpx.Response(code))
    assert outcome.status == "down"
    assert outcome.status_code == code
    assert outcome.error_message == f"HTTP {code}"
    assert outcome.response_time_ms is not None


def test_timeout_is_down():
    def handler(request):
        raise httpx.ReadTimeout("secret detail")

    outcome = check(handler)
    assert outcome.status == "down"
    assert outcome.status_code is None
    assert outcome.response_time_ms is None
    assert outcome.error_message == "Request timed out"


def test_connection_failure_is_down():
    def handler(request):
        raise httpx.ConnectError("secret detail")

    outcome = check(handler)
    assert outcome.status == "down"
    assert outcome.error_message == "Could not connect to host"


def test_unexpected_http_error_does_not_leak_details():
    def handler(request):
        raise httpx.DecodingError("secret-token-123")

    outcome = check(handler)
    assert outcome.error_message == "Request failed"
    assert "secret" not in repr(outcome)


def test_unresolvable_host_is_down_not_an_exception():
    # Regression test: this used to escape as an unhandled exception (HTTP 500).
    outcome = perform_check("http://nonexistent.invalid/")
    assert outcome.status == "down"
    assert outcome.error_message == "Could not resolve host"


def test_follows_redirects_to_final_response():
    def handler(request):
        if request.url.path == "/":
            return httpx.Response(302, headers={"location": "/a"})
        if request.url.path == "/a":
            return httpx.Response(301, headers={"location": "https://other.example/b"})
        return httpx.Response(200)

    outcome = check(handler)
    assert outcome.status == "up"
    assert outcome.status_code == 200


def test_redirect_loop_is_stopped():
    outcome = check(lambda request: httpx.Response(302, headers={"location": "/"}))
    assert outcome.status == "down"
    assert outcome.error_message == "Too many redirects"


@pytest.mark.parametrize(
    "target",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1/admin",
        "http://internal.example/admin",
        "ftp://good.example/file",
    ],
)
def test_redirect_to_restricted_destination_is_blocked(target):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": target})

    outcome = check(handler)
    assert outcome.status == "down"
    assert outcome.error_message == "Redirect to a restricted destination blocked"
    assert requested == [URL]  # the restricted URL was never requested


@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://internal.example/", "http://localhost/"])
def test_unsafe_initial_url_raises_and_sends_no_request(url):
    def handler(request):
        raise AssertionError("no request should be sent")

    with pytest.raises(UnsafeURLError):
        check(handler, url)


def test_redirect_without_location_is_treated_as_final_response():
    outcome = check(lambda request: httpx.Response(301))
    assert outcome.status == "up"
    assert outcome.status_code == 301
