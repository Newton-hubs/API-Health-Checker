import pytest

from app.services.ssrf import HostResolutionError, UnsafeURLError, validate_public_url

BLOCKED = [
    "http://127.0.0.1",
    "http://localhost",
    "http://10.0.0.1",
    "http://172.16.0.1",
    "http://192.168.1.1",
    "http://169.254.169.254/latest/meta-data/",
    "http://0.0.0.0",
    "http://[::1]",
    "http://[::ffff:127.0.0.1]",
    "http://[fe80::1]",
    "http://100.64.0.1",
    "http://224.0.0.1",
    "http://[64:ff9b::7f00:1]",  # NAT64 form of 127.0.0.1
    "http://[64:ff9b::a00:1]",  # NAT64 form of 10.0.0.1
    "http://[64:ff9b:1::1]",
    "http://[::127.0.0.1]",  # deprecated IPv4-compatible form
    "http://[2002:7f00:1::]",  # 6to4 form of 127.0.0.1
    "http://[2002:a9fe:a9fe::]",  # 6to4 form of 169.254.169.254
    "http://internal.example",
    "http://mixed.example",
    "ftp://93.184.216.34",
    "file:///etc/passwd",
    "http://93.184.216.34:99999",
    "http://",
]

ALLOWED = [
    "http://93.184.216.34",
    "https://93.184.216.34:8443/x",
    "http://[2606:2800:220:1:248:1893:25c8:1946]",
    "https://good.example/path?q=1",
]


@pytest.mark.parametrize("url", BLOCKED)
def test_blocks_unsafe_destinations(url):
    with pytest.raises(UnsafeURLError):
        validate_public_url(url)


@pytest.mark.parametrize("url", ALLOWED)
def test_allows_public_destinations(url):
    validate_public_url(url)  # must not raise


def test_unresolvable_host_raises_resolution_error():
    with pytest.raises(HostResolutionError):
        validate_public_url("http://nonexistent.invalid/")
