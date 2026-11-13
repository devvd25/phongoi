"""Block crawler requests that could reach local or otherwise non-public networks."""

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit


def _require_global(address: str) -> None:
    ip = ipaddress.ip_address(address)
    if not ip.is_global:
        raise ValueError("Crawler URL resolves to a non-public network")


def validate_url(value: str, *, resolve_dns: bool = True) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Crawler URL must use public HTTP or HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Crawler URL must not contain credentials")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith((".local", ".internal")):
        raise ValueError("Crawler URL must not target a local hostname")
    try:
        _require_global(hostname)
    except ValueError as exc:
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            if resolve_dns:
                addresses = {item[4][0] for item in socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM)}
                if not addresses:
                    raise ValueError("Crawler hostname did not resolve") from exc
                for address in addresses:
                    _require_global(address)
        else:
            raise exc
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))


class PublicNetworkOnlyMiddleware:
    """Validate the initial request, followed links and every redirect target."""

    def process_request(self, request, spider):
        from scrapy.exceptions import IgnoreRequest

        try:
            validate_url(request.url, resolve_dns=True)
        except (OSError, ValueError) as exc:
            spider.logger.warning("Blocked unsafe crawler request: %s", exc)
            raise IgnoreRequest(str(exc)) from exc
        return None
