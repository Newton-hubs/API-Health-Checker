import ipaddress
import socket
from urllib.parse import urlsplit


# Ranges that Python reports as "global" but which can embed or translate to an IPv4
# address (NAT64 and the deprecated IPv4-compatible form), bypassing the IPv4 checks.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("64:ff9b:1::/48"),
    ipaddress.ip_network("::/96"),
]


class UnsafeURLError(Exception):
    """The destination is not allowed (bad scheme or non-public address)."""


class HostResolutionError(Exception):
    """The hostname could not be resolved by DNS."""


def validate_public_url(url: str) -> None:
    """Raise UnsafeURLError unless every address behind `url` is publicly routable."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnsafeURLError("URL scheme or host is not allowed")

    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError:
        raise UnsafeURLError("URL port is not valid")

    try:
        infos = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HostResolutionError("Could not resolve host")

    # A hostname can map to several addresses; every one of them must be safe.
    for info in infos:
        address = info[4][0].split("%")[0]  # drop IPv6 scope id such as "fe80::1%eth0"
        ip = ipaddress.ip_address(address)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast or any(ip in net for net in _BLOCKED_NETWORKS):
            raise UnsafeURLError("Destination address is not allowed")
