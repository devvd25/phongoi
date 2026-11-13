"""Validation for network destinations controlled by crawler administrators."""

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit


def _public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return ip.is_global


def validate_public_http_url(value: str, *, resolve_dns: bool = False) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL phải dùng http/https và có tên miền hợp lệ")
    if parsed.username or parsed.password:
        raise ValueError("URL không được chứa tài khoản hoặc mật khẩu")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("URL không được trỏ vào mạng nội bộ")
    try:
        if not _public_ip(host):
            raise ValueError("URL không được trỏ vào IP riêng hoặc IP đặc biệt")
    except ValueError as exc:
        if "does not appear" not in str(exc):
            raise
    if resolve_dns:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
        if not addresses or any(not _public_ip(address) for address in addresses):
            raise ValueError("Tên miền nguồn phân giải tới mạng nội bộ hoặc IP đặc biệt")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))
