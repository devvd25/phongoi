from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


ROOT = Path(__file__).resolve().parents[1]


def test_alembic_upgrades_an_empty_database(tmp_path):
    """Bỏ migration hoặc metadata model sẽ làm database mới thiếu bảng nghiệp vụ."""
    database = tmp_path / "migration.db"
    cfg = Config(ROOT / "alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")

    command.upgrade(cfg, "head")

    tables = set(inspect(create_engine(f"sqlite:///{database.as_posix()}")).get_table_names())
    assert {"alembic_version", "users", "listings", "crawl_sources", "app_settings"} <= tables
