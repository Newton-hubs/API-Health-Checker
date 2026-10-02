import os

# Must run before any `app` import: tests must never touch the real database file.
os.environ["DATABASE_URL"] = "sqlite://"

import ipaddress
import socket

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models import health_check  # noqa: F401  (registers the table on Base.metadata)

PUBLIC_IP = "93.184.216.34"

# The only hostnames that "exist" during tests. Anything else fails to resolve.
FAKE_HOSTS = {
    "good.example": [PUBLIC_IP],
    "other.example": ["1.1.1.1"],  # documentation ranges (198.51.100.x etc.) are NOT global
    "internal.example": ["10.0.0.5"],
    "mixed.example": [PUBLIC_IP, "10.0.0.5"],  # one public and one private record
    "localhost": ["127.0.0.1"],
}


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    """Replace DNS so the *real* SSRF validator runs without any network lookups."""

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host in FAKE_HOSTS:
            ips = FAKE_HOSTS[host]
        else:
            try:
                ipaddress.ip_address(host)  # IP literals resolve to themselves
                ips = [host]
            except ValueError:
                raise socket.gaierror("fake DNS: unknown host")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in ips]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def _no_network(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"test attempted a real HTTP request to {request.url}")


@pytest.fixture(autouse=True)
def mock_http(monkeypatch):
    """Route every httpx.Client the app creates to a fake handler. Returns `use(handler)`."""
    state = {"handler": _no_network}
    real_client = httpx.Client

    def client_factory(**kwargs):
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(lambda request: state["handler"](request))
        return real_client(**kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)

    def use(handler):
        state["handler"] = handler

    return use


@pytest.fixture
def engine():
    # StaticPool: every connection shares the single in-memory database.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine):
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture
def client(engine):
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
