"""Unit tests for utility.ipv6_utils module."""

from unittest.mock import patch

import pytest

from utility.ipv6_utils import (
    format_ip_for_ceph_mon,
    format_ip_for_url,
    is_ipv6_address,
    resolve_hostname,
)


class TestIsIpv6Address:
    def test_ipv6_full(self):
        assert is_ipv6_address("fd00::a01:70a6") is True

    def test_ipv6_loopback(self):
        assert is_ipv6_address("::1") is True

    def test_ipv6_full_form(self):
        assert is_ipv6_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334") is True

    def test_ipv4(self):
        assert is_ipv6_address("10.1.1.100") is False

    def test_ipv4_loopback(self):
        assert is_ipv6_address("127.0.0.1") is False

    def test_hostname(self):
        assert is_ipv6_address("example.com") is False

    def test_empty_string(self):
        assert is_ipv6_address("") is False

    def test_garbage(self):
        assert is_ipv6_address("not-an-ip") is False


class TestFormatIpForUrl:
    def test_ipv6_gets_brackets(self):
        assert format_ip_for_url("fd00::a01:70a6") == "[fd00::a01:70a6]"

    def test_ipv4_unchanged(self):
        assert format_ip_for_url("10.1.1.100") == "10.1.1.100"

    def test_hostname_unchanged(self):
        assert format_ip_for_url("example.com") == "example.com"


class TestFormatIpForCephMon:
    def test_ipv6_gets_brackets(self):
        assert format_ip_for_ceph_mon("fd00::1") == "[fd00::1]"

    def test_ipv4_unchanged(self):
        assert format_ip_for_ceph_mon("172.16.0.1") == "172.16.0.1"


class TestResolveHostname:
    @patch("utility.ipv6_utils.socket.getaddrinfo")
    def test_resolve_ipv4(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("10.1.1.100", 0)),
        ]
        result = resolve_hostname("example.com", prefer_ipv6=False)
        assert result == "10.1.1.100"

    @patch("utility.ipv6_utils.socket.getaddrinfo")
    def test_resolve_ipv6(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (10, 1, 6, "", ("fd00::1", 0, 0, 0)),
        ]
        result = resolve_hostname("example.com", prefer_ipv6=True)
        assert result == "fd00::1"

    @patch("utility.ipv6_utils.socket.getaddrinfo")
    def test_fallback_to_other_family(self, mock_getaddrinfo):
        import socket

        def side_effect(hostname, port, family, socktype):
            if family == socket.AF_INET6:
                raise socket.gaierror("no AAAA record")
            return [(2, 1, 6, "", ("10.1.1.100", 0))]

        mock_getaddrinfo.side_effect = side_effect
        result = resolve_hostname("example.com", prefer_ipv6=True)
        assert result == "10.1.1.100"

    @patch("utility.ipv6_utils.socket.getaddrinfo")
    def test_raises_on_failure(self, mock_getaddrinfo):
        import socket

        mock_getaddrinfo.side_effect = socket.gaierror("not found")
        with pytest.raises(socket.gaierror):
            resolve_hostname("nonexistent.invalid")
