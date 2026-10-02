import time
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.core.config import CHECK_TIMEOUT_SECONDS, MAX_REDIRECTS
from app.services.ssrf import HostResolutionError, UnsafeURLError, validate_public_url

USER_AGENT = "API-Health-Checker/0.1"


@dataclass
class CheckOutcome:
    status: str  # "up" or "down"
    status_code: int | None
    response_time_ms: float | None
    error_message: str | None


def _down(message: str, status_code: int | None = None, elapsed: float | None = None) -> CheckOutcome:
    ms = round(elapsed * 1000, 2) if elapsed is not None else None
    return CheckOutcome("down", status_code, ms, message)


def perform_check(url: str, transport: httpx.BaseTransport | None = None) -> CheckOutcome:
    """Request `url` and classify the result.

    Raises UnsafeURLError if the *initial* URL is not allowed; every other
    failure is returned as a "down" outcome with a fixed, safe message.
    """
    try:
        validate_public_url(url)  # UnsafeURLError propagates (route turns it into a 400)
    except HostResolutionError:
        return _down("Could not resolve host")

    elapsed = 0.0
    current = url
    try:
        # trust_env=False: ignore proxy env vars, which would resolve DNS on our behalf.
        # follow_redirects=False: we follow redirects ourselves to vet every hop.
        with httpx.Client(
            timeout=CHECK_TIMEOUT_SECONDS,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": USER_AGENT},
            transport=transport,
        ) as client:
            for _ in range(MAX_REDIRECTS + 1):
                started = time.perf_counter()
                # stream() returns once headers arrive; we never download the body.
                with client.stream("GET", current) as response:
                    elapsed += time.perf_counter() - started
                    status_code = response.status_code
                    location = response.headers.get("location")
                    is_redirect = response.is_redirect

                if not (is_redirect and location):
                    if status_code >= 400:
                        return _down(f"HTTP {status_code}", status_code, elapsed)
                    return CheckOutcome("up", status_code, round(elapsed * 1000, 2), None)

                current = urljoin(current, location)
                try:
                    validate_public_url(current)
                except UnsafeURLError:
                    return _down("Redirect to a restricted destination blocked", status_code, elapsed)
            return _down("Too many redirects", None, elapsed)
    except HostResolutionError:
        return _down("Could not resolve host")
    except httpx.TimeoutException:
        return _down("Request timed out")
    except httpx.ConnectError:
        return _down("Could not connect to host")
    except (httpx.HTTPError, httpx.InvalidURL):
        return _down("Request failed")
