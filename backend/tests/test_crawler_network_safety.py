import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[2] / "crawler" / "phongoi_crawler" / "network_safety.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("crawler_network_safety", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.validate_url


def test_crawler_rejects_private_ip_on_every_request():
    with pytest.raises(ValueError):
        load_validator()("http://127.0.0.1/admin", resolve_dns=False)


def test_crawler_rejects_redirect_urls_with_credentials():
    with pytest.raises(ValueError):
        load_validator()("https://user:password@example.com/", resolve_dns=False)


def test_crawler_accepts_plain_public_https_url():
    assert load_validator()("https://example.com/listings", resolve_dns=False) == "https://example.com/listings"
