from pathlib import Path
from types import SimpleNamespace

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app import docker_bootstrap, search
from app.db import utcnow
from app.models import AppSetting, CrawlSource, Listing, ListingSource, ListingStat, School, User


ROOT = Path(__file__).resolve().parents[1]


def _migrated_engine(db_path: Path):
    cfg = Config(ROOT / "alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    command.upgrade(cfg, "head")
    return create_engine(f"sqlite:///{db_path.as_posix()}")


def test_bootstrap_migrates_sqlite_once_and_preserves_existing_data(tmp_path):
    src_path = tmp_path / "src.db"
    dst_path = tmp_path / "dst.db"
    src_engine = _migrated_engine(src_path)
    dst_engine = _migrated_engine(dst_path)

    SrcSession = sessionmaker(bind=src_engine, autoflush=False, expire_on_commit=False)
    with SrcSession() as db:
        school = School(name="DH Bach khoa", short_name="DUT", district="Lien Chieu", lat=16.0738, lng=108.1499, aliases=["bach khoa"])
        user = User(email="admin@phongoi.vn", password_hash="hashed", full_name="Admin", role="admin")
        src = CrawlSource(
            name="Chotot Da Nang",
            kind="scrapy",
            spider="generic",
            start_url="https://www.chotot.com/da-nang/thue-phong-tro",
            frequency_minutes=30,
            enabled=True,
            status="ok",
            config={"item_css": "li"},
        )
        db.add_all([school, user, src])
        db.flush()
        listing = Listing(
            title="Phong tro gan DH Bach khoa",
            description="Day du tien nghi, dien 3.5k",
            price=2_000_000,
            area=22.0,
            district="Lien Chieu",
            street="Nguyen Luong Bang",
            address="12 Nguyen Luong Bang, Lien Chieu",
            room_type="phong_tro",
            amenities=["may_lanh", "wifi"],
            images=["/rooms/room-1.jpg"],
            status="active",
            owner_id=user.id,
            source_count=1,
            posted_at=utcnow(),
        )
        db.add(listing)
        db.flush()
        db.add(
            ListingSource(
                listing_id=listing.id,
                source_name="Chotot Da Nang",
                url="https://www.chotot.com/123.htm",
                posted_at=utcnow(),
                raw_text="Phong tro gan DH Bach khoa",
            )
        )
        db.add(AppSetting(key="dataset_meta", value={"mode": "live", "seeded": True}))
        db.commit()

    first = docker_bootstrap.bootstrap_database(target_engine=dst_engine, sqlite_path=src_path, index_es=False, sync_registry=False)
    assert first["action"] == "migrated_sqlite"
    assert first["listings"] == 1

    DstSession = sessionmaker(bind=dst_engine, autoflush=False, expire_on_commit=False)
    with DstSession() as db:
        assert db.query(Listing).count() == 1
        assert db.query(CrawlSource).filter_by(name="Chotot Da Nang", enabled=True).count() == 1
        assert db.query(ListingSource).count() == 1
        assert db.query(AppSetting).filter_by(key="dataset_meta").first().value["mode"] == "live"
        # Simulate new listing crawled in Docker later
        db.add(
            Listing(
                title="Phong moi thu thap tu Docker",
                description="Tin moi",
                price=2_500_000,
                area=25.0,
                district="Hai Chau",
                address="10 Le Duan, Hai Chau",
                room_type="phong_tro",
                amenities=[],
                images=[],
                status="active",
                source_count=1,
                posted_at=utcnow(),
            )
        )
        db.commit()

    second = docker_bootstrap.bootstrap_database(target_engine=dst_engine, sqlite_path=src_path, index_es=False, sync_registry=False)
    assert second["action"] == "preserved"
    with DstSession() as db:
        titles = {r.title for r in db.query(Listing).all()}
        assert titles == {"Phong tro gan DH Bach khoa", "Phong moi thu thap tu Docker"}


def test_bootstrap_seeds_once_when_empty_without_sqlite(tmp_path):
    dst_path = tmp_path / "empty.db"
    dst_engine = _migrated_engine(dst_path)
    seed_calls = []

    def fake_seed():
        seed_calls.append(1)
        DstSession = sessionmaker(bind=dst_engine, autoflush=False, expire_on_commit=False)
        with DstSession() as db:
            db.add(User(email="seeded@phongoi.vn", password_hash="x", full_name="Seeded", role="admin"))
            db.commit()

    res1 = docker_bootstrap.bootstrap_database(
        target_engine=dst_engine,
        sqlite_path=tmp_path / "missing.db",
        seed_fn=fake_seed,
        index_es=False,
        sync_registry=False,
    )
    res2 = docker_bootstrap.bootstrap_database(
        target_engine=dst_engine,
        sqlite_path=tmp_path / "missing.db",
        seed_fn=fake_seed,
        index_es=False,
        sync_registry=False,
    )
    assert res1["action"] == "seeded"
    assert res2["action"] == "preserved"
    assert len(seed_calls) == 1


def test_es_retries_after_initial_startup_failure(monkeypatch):
    import elasticsearch as es_mod

    state = {"ping_calls": 0, "now": 100.0}

    class FakeIndices:
        def exists(self, index):
            return True

        def create(self, index, settings, mappings):
            pass

    class FakeES:
        def __init__(self, *args, **kwargs):
            self.indices = FakeIndices()

        def ping(self):
            state["ping_calls"] += 1
            return state["ping_calls"] >= 2

    monkeypatch.setattr(search, "_es", {"client": None, "checked": False, "last_attempt": 0.0})
    monkeypatch.setattr(search, "settings", SimpleNamespace(elasticsearch_url="http://elasticsearch:9200", es_index="phongoi"))
    monkeypatch.setattr(es_mod, "Elasticsearch", FakeES)
    monkeypatch.setattr(search.time, "monotonic", lambda: state["now"])

    assert search.es() is None
    # Before cooldown expires, stays cached as None without hammering ES
    state["now"] += 2.0
    assert search.es() is None
    assert state["ping_calls"] == 1
    # After cooldown expires, retries and connects cleanly
    state["now"] += 20.0
    client = search.es()
    assert client is not None
    assert state["ping_calls"] == 2


def test_ensure_alembic_stamps_legacy_create_all_db(tmp_path):
    legacy_path = tmp_path / "legacy.db"
    cfg = Config(ROOT / "alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{legacy_path.as_posix()}")
    # Simulate an older create_all schema at initial_schema revision without alembic_version table
    command.upgrade(cfg, "1a20f1481fdc")
    legacy_engine = create_engine(f"sqlite:///{legacy_path.as_posix()}")
    with legacy_engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE alembic_version")

    status = docker_bootstrap.ensure_alembic_version(target_engine=legacy_engine, alembic_cfg=cfg)
    assert status == "stamped_1a20f1481fdc"

    # Subsequent upgrade to head must succeed without DuplicateTable errors
    command.upgrade(cfg, "head")
    with legacy_engine.connect() as conn:
        rev = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(crawl_sources)")}
    assert rev == "8b6c5a2f4d01"
    assert "profile_id" in cols


def test_bootstrap_skips_orphan_foreign_keys_during_sqlite_migration(tmp_path):
    src_path = tmp_path / "dirty_src.db"
    dst_path = tmp_path / "strict_dst.db"
    src_engine = _migrated_engine(src_path)
    dst_engine = _migrated_engine(dst_path)

    # Enforce strict FK checking on target engine just like PostgreSQL
    @event.listens_for(dst_engine, "connect")
    def _enable_fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    SrcSession = sessionmaker(bind=src_engine, autoflush=False, expire_on_commit=False)
    with SrcSession() as db:
        listing = Listing(
            title="Phong hop le",
            description="Mo ta",
            price=2_000_000,
            area=20.0,
            district="Lien Chieu",
            address="10 Nguyen Luong Bang",
            room_type="phong_tro",
            amenities=[],
            images=[],
            status="active",
            owner_id=888,  # dangling nullable owner_id
            source_count=1,
            posted_at=utcnow(),
        )
        db.add(listing)
        db.flush()
        # dangling non-nullable listing_id=999
        db.add(ListingStat(listing_id=999, day=utcnow().date(), views=3))
        db.add(ListingStat(listing_id=listing.id, day=utcnow().date(), views=5))
        db.commit()

    res = docker_bootstrap.bootstrap_database(target_engine=dst_engine, sqlite_path=src_path, index_es=False, sync_registry=False)
    assert res["action"] == "migrated_sqlite"
    assert res["listings"] == 1

    DstSession = sessionmaker(bind=dst_engine, autoflush=False, expire_on_commit=False)
    with DstSession() as db:
        migrated_listing = db.query(Listing).one()
        assert migrated_listing.owner_id is None
        stats = db.query(ListingStat).all()
        assert len(stats) == 1
        assert stats[0].views == 5

