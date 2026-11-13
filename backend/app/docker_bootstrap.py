"""Khoi tao va dong bo du lieu PostgreSQL/Elasticsearch khi chay Docker lan dau.

Nguyen tac an toan:
- Chi nhap tu SQLite hoac seed du lieu mau khi database dich dang trong hoan toan.
- Cac lan khoi dong sau luon giu nguyen toan bo du lieu da thu thap trong volume Docker.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Callable

import sqlalchemy as sa
from sqlalchemy import create_engine, func, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from . import catalog_store, models  # noqa: F401 - dam bao Base.metadata du cac bang
from .db import Base, engine as default_engine
from .models import CrawlSource, Listing, User
from .search import es, reindex_all
from .source_registry import sync_source_registry


def is_database_empty(db) -> bool:
    return (
        db.query(func.count(User.id)).scalar() == 0
        and db.query(func.count(Listing.id)).scalar() == 0
        and db.query(func.count(CrawlSource.id)).scalar() == 0
    )


def _sqlite_has_data(sqlite_path: Path) -> bool:
    if not sqlite_path.is_file():
        return False
    con = sqlite3.connect(f"file:{sqlite_path.as_posix()}?mode=ro", uri=True)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for tbl in ("users", "listings", "crawl_sources"):
            if tbl in tables and con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0] > 0:
                return True
        return False
    finally:
        con.close()


def _reset_postgres_sequences(conn) -> None:
    if conn.dialect.name != "postgresql":
        return
    for table in Base.metadata.sorted_tables:
        if "id" not in table.c or not table.c.id.primary_key:
            continue
        seq = conn.execute(
            text("SELECT pg_get_serial_sequence(:tbl, 'id')"),
            {"tbl": table.name},
        ).scalar()
        if not seq:
            continue
        max_id = conn.execute(sa.select(func.max(table.c.id))).scalar()
        if max_id is None:
            conn.execute(text("SELECT setval(:seq, 1, false)"), {"seq": seq})
        else:
            conn.execute(text("SELECT setval(:seq, :val, true)"), {"seq": seq, "val": int(max_id)})


def _sanitize_fk_rows(table: sa.Table, rows: list[dict], copied_keys: dict[tuple[str, str], set]) -> list[dict]:
    if not table.foreign_keys:
        return rows
    fks = list(table.foreign_keys)
    clean: list[dict] = []
    for row in rows:
        keep = True
        for fk in fks:
            col_name = fk.parent.name
            val = row.get(col_name)
            if val is None:
                continue
            valid_targets = copied_keys.get((fk.column.table.name, fk.column.name), set())
            if val not in valid_targets:
                if fk.parent.nullable:
                    row[col_name] = None
                else:
                    keep = False
                    break
        if keep:
            clean.append(row)
    return clean


def migrate_sqlite_to_target(sqlite_path: Path, target_engine: Engine, chunk_size: int = 500) -> dict[str, int]:
    src_engine = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    src_tables = set(inspect(src_engine).get_table_names())
    copied: dict[str, int] = {}
    copied_keys: dict[tuple[str, str], set] = {}

    try:
        with src_engine.connect() as src_conn, target_engine.begin() as dst_conn:
            for table in Base.metadata.sorted_tables:
                if table.name not in src_tables:
                    continue
                rows = [dict(row) for row in src_conn.execute(sa.select(table)).mappings().all()]
                rows = _sanitize_fk_rows(table, rows, copied_keys)
                for col in table.columns:
                    if col.primary_key or col.unique:
                        copied_keys[(table.name, col.name)] = {r[col.name] for r in rows if r.get(col.name) is not None}
                if not rows:
                    copied[table.name] = 0
                    continue
                for idx in range(0, len(rows), chunk_size):
                    dst_conn.execute(table.insert(), rows[idx : idx + chunk_size])
                copied[table.name] = len(rows)
            _reset_postgres_sequences(dst_conn)
    finally:
        src_engine.dispose()

    return copied


def _es_doc_count() -> int | None:
    client = es()
    if not client:
        return None
    try:
        from .config import settings

        if not client.indices.exists(index=settings.es_index):
            return 0
        return int(client.count(index=settings.es_index).get("count", 0))
    except Exception:
        return None


def bootstrap_database(
    target_engine: Engine | None = None,
    sqlite_path: Path | None = None,
    seed_fn: Callable[[], None] | None = None,
    index_es: bool = True,
    sync_registry: bool = True,
) -> dict:
    target = target_engine or default_engine
    Session = sessionmaker(bind=target, autoflush=False, expire_on_commit=False)

    with Session() as db:
        empty = is_database_empty(db)
        if not empty:
            if sync_registry:
                sync_source_registry(db)
            catalog_store.apply(db)
            listings_count = db.query(func.count(Listing.id)).scalar() or 0
            es_indexed = 0
            if index_es and listings_count > 0:
                doc_count = _es_doc_count()
                if doc_count == 0:
                    es_indexed = reindex_all(db)
            return {
                "action": "preserved",
                "users": db.query(func.count(User.id)).scalar() or 0,
                "listings": listings_count,
                "sources": db.query(func.count(CrawlSource.id)).scalar() or 0,
                "es_indexed": es_indexed,
            }

    if sqlite_path and _sqlite_has_data(sqlite_path):
        copied = migrate_sqlite_to_target(sqlite_path, target)
        with Session() as db:
            if sync_registry:
                sync_source_registry(db)
            catalog_store.apply(db)
            es_indexed = reindex_all(db) if index_es else 0
            return {
                "action": "migrated_sqlite",
                "users": copied.get("users", 0),
                "listings": copied.get("listings", 0),
                "sources": db.query(func.count(CrawlSource.id)).scalar() or 0,
                "es_indexed": es_indexed,
            }

    if seed_fn is None:
        from . import seed as seed_module

        seed_fn = seed_module.run
    seed_fn()

    with Session() as db:
        catalog_store.apply(db)
        es_indexed = 0
        if index_es:
            doc_count = _es_doc_count()
            if doc_count == 0 and (db.query(func.count(Listing.id)).scalar() or 0) > 0:
                es_indexed = reindex_all(db)
        return {
            "action": "seeded",
            "users": db.query(func.count(User.id)).scalar() or 0,
            "listings": db.query(func.count(Listing.id)).scalar() or 0,
            "sources": db.query(func.count(CrawlSource.id)).scalar() or 0,
            "es_indexed": es_indexed,
        }


def ensure_alembic_version(
    target_engine: Engine | None = None,
    alembic_cfg=None,
) -> str:
    """Stamp legacy pre-Alembic databases (created via Base.metadata.create_all) so upgrade head succeeds cleanly."""
    from alembic import command
    from alembic.config import Config

    target = target_engine or default_engine
    inspector = inspect(target)
    tables = set(inspector.get_table_names())
    if "alembic_version" in tables:
        return "alembic_present"
    if not ({"users", "listings", "crawl_sources"} & tables):
        return "fresh_database"

    cfg = alembic_cfg
    if cfg is None:
        cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))

    cols = {col["name"] for col in inspector.get_columns("crawl_sources")} if "crawl_sources" in tables else set()
    rev = "8b6c5a2f4d01" if "profile_id" in cols else "1a20f1481fdc"
    command.stamp(cfg, rev)
    return f"stamped_{rev}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Docker PostgreSQL database once without overwriting existing data.")
    parser.add_argument("--sqlite", type=Path, default=None, help="Optional SQLite DB file to import if target DB is empty.")
    parser.add_argument("--check-empty", action="store_true", help="Exit 10 if target DB is empty, 0 if already populated.")
    parser.add_argument("--ensure-alembic", action="store_true", help="Stamp legacy pre-Alembic DB before alembic upgrade head.")
    args = parser.parse_args(argv)

    if args.ensure_alembic:
        status = ensure_alembic_version()
        print(f"[docker-bootstrap] ensure_alembic={status}")
        return 0

    if args.check_empty:
        Session = sessionmaker(bind=default_engine, autoflush=False, expire_on_commit=False)
        with Session() as db:
            empty = is_database_empty(db)
        print("EMPTY=1" if empty else "EMPTY=0")
        return 10 if empty else 0

    result = bootstrap_database(sqlite_path=args.sqlite)
    print(
        f"[docker-bootstrap] action={result['action']} "
        f"users={result['users']} listings={result['listings']} "
        f"sources={result['sources']} es_indexed={result['es_indexed']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

