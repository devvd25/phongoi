import os
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///./test_phongoi.db"
os.environ["LLM_PROVIDER"] = "none"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app import seed  # noqa: E402
from app.config import Settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CrawlRun, CrawlSource  # noqa: E402


RETIRED_SCHOOL_SOURCE_IDS = {
    "duytan-housing",
    "ktx-danang",
    "ktx-dut",
    "ktx-ued",
    "ktx-due",
    "ktx-vku",
    "ktx-fpt",
    "housing-ute",
    "housing-donga",
}
RENTAL_PORTAL_SOURCE_IDS = {
    "guland",
    "chothuenha",
    "batdongsanonline",
    "thuenhatro",
    "bds123",
    "soinha",
    "thuephongtro-com",
    "dithuenha",
    "nhadatcanban",
}


@pytest.fixture(scope="module")
def client():
    seed.run()
    return TestClient(app)


def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@phongoi.vn", "password": "Admin@2026"},
    )
    return {"Authorization": "Bearer " + response.json()["token"]}


def test_production_rejects_default_security_tokens():
    """A deployment must not be able to start with the documented development secrets."""
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="dev-secret-change-me",
            ingest_token="dev-ingest-token",
            _env_file=None,
        )


def test_production_does_not_create_schema_at_application_startup():
    settings = Settings(
        app_env="production",
        jwt_secret="j" * 40,
        ingest_token="i" * 40,
        _env_file=None,
    )
    assert settings.auto_create_schema is False


def test_admin_overview_marks_seeded_dataset_as_demo(client):
    """Operators must be able to distinguish seeded dashboard metrics from live data."""
    dataset = client.get("/api/admin/overview", headers=admin_headers(client)).json()["dataset"]
    assert dataset == {"mode": "demo", "label": "Dữ liệu minh họa", "seeded": True}


def test_admin_exposes_validated_crawler_profiles(client):
    """Crawler setup should start from a versioned profile instead of blank selectors."""
    response = client.get("/api/admin/source-profiles", headers=admin_headers(client))
    assert response.status_code == 200
    profiles = response.json()
    assert profiles
    assert all(p["config"]["item_selector"] for p in profiles)
    assert all(not p["config"]["terms_checked"] for p in profiles if p["connector_type"] != "first_party")


def test_source_registry_contains_50_unique_disabled_profiles(client):
    """Losing a registry entry or shipping a pre-approved external source must fail CI."""
    profiles = client.get("/api/admin/source-profiles", headers=admin_headers(client)).json()
    from app.source_profiles import profiles as get_profiles
    expected_total = len(get_profiles())
    assert len(profiles) == expected_total
    assert len({profile["id"] for profile in profiles}) == expected_total
    assert all(profile["connector_type"] for profile in profiles)
    assert all(profile["integration_status"] in {"ready", "legal_review", "partner_required"} for profile in profiles)
    assert all(not profile["config"]["terms_checked"] for profile in profiles if profile["connector_type"] != "first_party")


def test_registry_replaces_school_sources_with_active_rental_portals(client):
    """The collection registry should contain rental inventory, not school notice pages."""
    profiles = client.get("/api/admin/source-profiles", headers=admin_headers(client)).json()
    profile_ids = {profile["id"] for profile in profiles}
    assert profile_ids.isdisjoint(RETIRED_SCHOOL_SOURCE_IDS)
    assert RENTAL_PORTAL_SOURCE_IDS <= profile_ids
    assert all("da-nang" in profile["start_url"] or "danang" in profile["start_url"] for profile in profiles if profile["id"] in RENTAL_PORTAL_SOURCE_IDS)


def test_admin_cannot_register_private_network_crawler_url(client):
    """A source URL must never turn the worker into an SSRF primitive."""
    response = client.post(
        "/api/admin/sources",
        headers=admin_headers(client),
        json={"name": "Metadata endpoint", "start_url": "http://169.254.169.254/latest/meta-data"},
    )
    assert response.status_code == 422


def test_admin_cannot_register_url_with_embedded_credentials(client):
    response = client.post(
        "/api/admin/sources",
        headers=admin_headers(client),
        json={"name": "Credential URL", "start_url": "https://user:secret@example.com/listings"},
    )
    assert response.status_code == 422


def test_seed_installs_registry_sources_as_paused(client):
    """A fresh environment exposes the full registry without silently crawling third parties."""
    from app.source_profiles import profiles as get_profiles
    expected_total = len(get_profiles())
    sources = client.get("/api/admin/sources", headers=admin_headers(client)).json()
    registry_sources = [source for source in sources if source.get("profile_id")]
    assert len(sources) == expected_total
    assert len(registry_sources) == expected_total
    assert all(source["kind"] != "sample" for source in sources)
    assert all(not source["enabled"] for source in registry_sources)
    assert all(source["integration_status"] in {"ready", "legal_review", "partner_required"} for source in registry_sources)


def test_registry_sync_is_idempotent(client):
    """Existing deployments can receive new profiles without resetting user data."""
    from app.source_profiles import profiles as get_profiles
    expected_total = len(get_profiles())
    headers = admin_headers(client)
    first = client.post("/api/admin/sources/sync-registry", headers=headers)
    second = client.post("/api/admin/sources/sync-registry", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["total"] == second.json()["total"] == expected_total
    assert second.json()["created"] == 0


def test_registry_sync_migrates_deprecated_profile_ids(client):
    from app.source_profiles import profiles as get_profiles
    expected_total = len(get_profiles())
    db = SessionLocal()
    source = db.query(CrawlSource).filter_by(profile_id="mairent").one()
    source.profile_id = "thuephongtro"
    db.commit()
    db.close()

    result = client.post("/api/admin/sources/sync-registry", headers=admin_headers(client))
    assert result.status_code == 200
    assert result.json()["total"] == expected_total
    db = SessionLocal()
    assert db.query(CrawlSource).filter_by(profile_id="thuephongtro").count() == 0
    assert db.query(CrawlSource).filter_by(profile_id="mairent").count() == 1
    db.close()


def test_registry_sync_deletes_retired_school_sources_and_their_runs(client):
    """A removed school connector must disappear from an existing deployment on sync."""
    db = SessionLocal()
    retired_sources = db.query(CrawlSource).filter(CrawlSource.profile_id.in_(RETIRED_SCHOOL_SOURCE_IDS)).all()
    retired_source_ids = [source.id for source in retired_sources]
    if retired_source_ids:
        db.query(CrawlRun).filter(CrawlRun.source_id.in_(retired_source_ids)).delete(synchronize_session=False)
        db.query(CrawlSource).filter(CrawlSource.id.in_(retired_source_ids)).delete(synchronize_session=False)
    legacy = CrawlSource(
        name="Nguồn trường cũ",
        kind="scrapy",
        spider="generic",
        profile_id="duytan-housing",
        start_url="https://nhatro.duytan.edu.vn/nha-tro/tim-phong-tro",
        enabled=True,
        status="ok",
    )
    db.add(legacy)
    db.flush()
    legacy_id = legacy.id
    db.add(CrawlRun(source_id=legacy_id, status="success"))
    db.commit()
    db.close()

    result = client.post("/api/admin/sources/sync-registry", headers=admin_headers(client))
    assert result.status_code == 200
    assert result.json()["retired"] == 1

    db = SessionLocal()
    assert db.query(CrawlSource).filter_by(id=legacy_id).count() == 0
    assert db.query(CrawlRun).filter_by(source_id=legacy_id).count() == 0
    db.close()


def test_run_enabled_sources_queues_collectors_but_not_first_party_sources(client):
    """The overview action must run real collectors without relying on deleted demo fixtures."""
    db = SessionLocal()
    collector = db.query(CrawlSource).filter_by(connector_type="rest_api").first()
    first_party = db.query(CrawlSource).filter_by(connector_type="first_party").first()
    assert collector is not None
    assert first_party is not None
    original = {
        collector.id: (collector.enabled, collector.status),
        first_party.id: (first_party.enabled, first_party.status),
    }
    collector.enabled = True
    collector.status = "ok"
    first_party.enabled = True
    first_party.status = "ok"
    collector_id = collector.id
    first_party_id = first_party.id
    db.commit()
    db.close()

    try:
        with patch("app.worker.crawl_source.delay") as delay:
            response = client.post("/api/admin/sources/run-enabled", headers=admin_headers(client))

        assert response.status_code == 200
        payload = response.json()
        assert payload["queued_count"] == 1
        assert [source["id"] for source in payload["queued"]] == [collector_id]
        delay.assert_called_once_with(collector_id)
    finally:
        db = SessionLocal()
        for source_id, (enabled, status) in original.items():
            source = db.get(CrawlSource, source_id)
            source.enabled = enabled
            source.status = status
        db.commit()
        db.close()
