"""Idempotent installation of versioned collection-source profiles."""

from sqlalchemy.orm import Session

from .models import CrawlRun, CrawlSource
from .source_profiles import profiles


PROFILE_ALIASES = {
    "thuephongtro": "mairent",
    "dothi": "dananghomii",
    "bannha": "danangflats",
    "batdongsanpro": "properly",
    "datvietvang": "livingdanang",
    "viraland": "nestvn",
    "reddit-danang": "green-residence",
}

RETIRED_PROFILE_IDS = {
    "duytan-housing",
    "ktx-danang",
    "ktx-dut",
    "ktx-ued",
    "ktx-due",
    "ktx-vku",
    "ktx-fpt",
    "housing-ute",
    "housing-donga",
    "facebook-groups",
    "fb-group-phongtro-danang-247",
    "fb-group-nhatro-sv-danang",
    "fb-group-canho-studio-danang",
    "fb-group-nha-nguyen-can-danang",
    "fb-group-phongtro-haichau-sontra",
}


def _apply_profile(source: CrawlSource, profile: dict) -> None:
    source.profile_id = profile["id"]
    source.name = profile["name"]
    source.kind = profile["kind"]
    source.spider = None if profile["kind"] == "manual" else "generic"
    source.start_url = profile["start_url"]
    source.config = profile["config"]
    source.connector_type = profile["connector_type"]
    source.integration_status = profile["integration_status"]


def sync_source_registry(db: Session) -> dict[str, int]:
    """Add missing profiles without overwriting operator settings or approvals."""
    registry = {profile["id"]: profile for profile in profiles()}
    retired_sources = db.query(CrawlSource).filter(CrawlSource.profile_id.in_(RETIRED_PROFILE_IDS)).all()
    retired_ids = [source.id for source in retired_sources]
    if retired_ids:
        db.query(CrawlRun).filter(CrawlRun.source_id.in_(retired_ids)).delete(synchronize_session=False)
        db.query(CrawlSource).filter(CrawlSource.id.in_(retired_ids)).delete(synchronize_session=False)
        db.flush()
    sources = {source.profile_id: source for source in db.query(CrawlSource).filter(CrawlSource.profile_id.is_not(None)).all()}
    migrated = 0
    for old_id, new_id in PROFILE_ALIASES.items():
        legacy = sources.get(old_id)
        if not legacy:
            continue
        if new_id in sources or legacy.approved_at or legacy.enabled:
            # Keep a potentially customized legacy source but detach it from the
            # versioned registry so future syncs remain idempotent.
            legacy.profile_id = None
            legacy.enabled = False
            legacy.status = "paused"
        else:
            _apply_profile(legacy, registry[new_id])
            sources[new_id] = legacy
        sources.pop(old_id, None)
        migrated += 1
    existing = set(sources)
    created = 0
    for profile in registry.values():
        if profile["id"] in existing:
            continue
        db.add(CrawlSource(
            name=profile["name"],
            kind=profile["kind"],
            spider=None if profile["kind"] == "manual" else "generic",
            start_url=profile["start_url"],
            frequency_minutes=60,
            enabled=False,
            status="paused",
            config=profile["config"],
            profile_id=profile["id"],
            profile_version=1,
            connector_type=profile["connector_type"],
            integration_status=profile["integration_status"],
        ))
        created += 1
    db.commit()
    total = db.query(CrawlSource).filter(CrawlSource.profile_id.is_not(None)).count()
    return {"created": created, "migrated": migrated, "retired": len(retired_ids), "total": total}
