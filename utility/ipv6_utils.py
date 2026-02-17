"""Centralized IPv6 utility functions for CephCI."""

import ipaddress
import socket


def is_ipv6_address(addr):
    """Check if the given address string is an IPv6 address.

    Args:
        addr (str): IP address string

    Returns:
        bool: True if addr is a valid IPv6 address, False otherwise
    """
    try:
        return isinstance(ipaddress.ip_address(str(addr)), ipaddress.IPv6Address)
    except ValueError:
        return False


def format_ip_for_url(addr):
    """Wrap IPv6 addresses in brackets for use in URLs.

    IPv4 addresses are returned unchanged. IPv6 addresses are wrapped
    in square brackets (e.g., ``[fd00::1]``).

    Args:
        addr (str): IP address string

    Returns:
        str: Bracket-wrapped address for IPv6, original for IPv4
    """
    if is_ipv6_address(addr):
        return f"[{addr}]"
    return addr


def format_ip_for_ceph_mon(addr):
    """Wrap IPv6 addresses in brackets for ceph mon host config entries.

    Ceph ``mon host`` configuration requires IPv6 addresses to be enclosed
    in square brackets. IPv4 addresses are returned unchanged.

    Args:
        addr (str): IP address string

    Returns:
        str: Bracket-wrapped address for IPv6, original for IPv4
    """
    if is_ipv6_address(addr):
        return f"[{addr}]"
    return addr


def resolve_hostname(hostname, prefer_ipv6=False):
    """Resolve a hostname to an IP address using getaddrinfo.

    Replaces ``socket.gethostbyname()`` with ``socket.getaddrinfo()`` to
    support both IPv4 and IPv6 resolution.

    Args:
        hostname (str): Hostname to resolve
        prefer_ipv6 (bool): If True, prefer AAAA records (AF_INET6).
            Defaults to False (AF_INET).

    Returns:
        str: Resolved IP address

    Raises:
        socket.gaierror: If the hostname cannot be resolved
    """
    family = socket.AF_INET6 if prefer_ipv6 else socket.AF_INET
    try:
        results = socket.getaddrinfo(hostname, None, family, socket.SOCK_STREAM)
        if results:
            return results[0][4][0]
    except socket.gaierror:
        pass

    # Fallback: try the other address family
    fallback_family = socket.AF_INET if prefer_ipv6 else socket.AF_INET6
    results = socket.getaddrinfo(hostname, None, fallback_family, socket.SOCK_STREAM)
    if results:
        return results[0][4][0]

    raise socket.gaierror(f"Unable to resolve hostname: {hostname}")
