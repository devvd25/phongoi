"""Tác vụ nền Celery: thu thập theo lịch, xử lý tin, đánh chỉ mục lại, chấm lại rủi ro.

Không cấu hình REDIS_URL thì Celery chạy đồng bộ (eager) để demo không cần Redis.
Chạy thật: celery -A app.worker worker -l info  và  celery -A app.worker beat -l info
"""

import json
import os
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

from celery import Celery

from . import catalog_store
from .config import settings
from .db import SessionLocal, utcnow
from .fb_group_bot import fetch_fb_group_posts
from .models import CrawlRun, CrawlSource, Listing, PipelineRun
from .notify import notify_admins
from .pipeline import RawPost, process_raw
from .risk import apply as apply_risk
from .search import reindex_all
from .source_connectors import apply_run_health, fetch_helprent, rate_limit_delay
from .url_safety import validate_public_http_url

celery_app = Celery("phongoi", broker=settings.redis_url or "memory://")
celery_app.conf.update(
    task_always_eager=not settings.redis_url,
    timezone="Asia/Ho_Chi_Minh",
    beat_schedule={
        "crawl-due-sources": {"task": "app.worker.crawl_due_sources", "schedule": 300.0},
        "recompute-risk-nightly": {"task": "app.worker.recompute_risk", "schedule": 24 * 3600.0},
    },
)


SELECTOR_KEYS = ("item_selector", "link_selector", "text_selector", "image_selector", "next_selector")


def scrapy_run_failed(returncode: int, output: str) -> bool:
    """Treat downloader/spider failures as failures even when Scrapy exits 0."""
    if returncode != 0:
        return True
    return any(
        marker in output
        for marker in (
            "'downloader/exception_count':",
            '"downloader/exception_count":',
            "'spider_exceptions/count':",
            '"spider_exceptions/count":',
            "'item_error_count':",
            '"item_error_count":',
            "Unhandled error in Deferred",
        )
    )


def run_scrapy_process(cmd: list[str], env: dict[str, str]):
    return subprocess.run(
        cmd,
        cwd=settings.crawler_dir,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )


def completed_run_status(error_count: int, collected: int, expects_items: bool) -> str:
    if error_count or (expects_items and collected == 0):
        return "partial"
    return "success"


def _fixtures() -> list[dict]:
    path = Path(settings.crawler_dir) / "fixtures" / "sample_posts.json"
    return json.loads(path.read_text(encoding="utf-8"))


@celery_app.task(name="app.worker.crawl_source")
def crawl_source(source_id: int) -> dict:
    db = SessionLocal()
    catalog_store.apply(db)
    t0 = time.time()
    src = db.get(CrawlSource, source_id)
    run = CrawlRun(source_id=source_id)
    db.add(run)
    src.status = "running"
    db.commit()
    collected = cleaned = 0
    try:
        if src.connector_type == "rest_api":
            for post in fetch_helprent(src.start_url, src.name, src.max_pages):
                collected += 1
                res = process_raw(db, post)
                if res["status"] == "new":
                    run.new_count += 1
                elif res["status"] == "duplicate":
                    run.dup_count += 1
                else:
                    run.error_count += 1
                if res.get("stage") != "clean":
                    cleaned += 1
        elif src.kind in ("internal", "manual"):
            pass  # tin chính chủ đăng trực tiếp trên hệ thống, không cần thu thập
        elif src.kind == "sample":
            for post in _fixtures():
                collected += 1
                res = process_raw(db, RawPost(**{**post, "source_name": post.get("source_name") or src.name}))
                if res["status"] == "new":
                    run.new_count += 1
                elif res["status"] == "duplicate":
                    run.dup_count += 1
                else:
                    run.error_count += 1
                if res.get("stage") != "clean":
                    cleaned += 1
        elif "facebook.com/groups/" in (src.start_url or "").lower():
            for post in fetch_fb_group_posts(src.start_url, src.name, max_posts=max(8, src.max_pages * 4)):
                collected += 1
                res = process_raw(db, post)
                if res["status"] == "new":
                    run.new_count += 1
                    cleaned += 1
                elif res["status"] == "duplicate":
                    run.dup_count += 1
                    cleaned += 1
                elif res.get("stage") == "clean":
                    # Bài tìm phòng / spam đã được ML CPU tự động lọc bỏ ở bước làm sạch
                    pass
                else:
                    run.error_count += 1
        else:
            validate_public_http_url(src.start_url, resolve_dns=True)
            env = {**os.environ, "BACKEND_URL": os.environ.get("BACKEND_URL", "http://localhost:8000"),
                   "INGEST_TOKEN": settings.ingest_token, "RUN_ID": str(run.id), "SOURCE_NAME": src.name}
            cmd = [sys.executable, "-m", "scrapy", "crawl", src.spider or "generic", "-a", f"start_url={src.start_url}",
                   "-a", f"max_pages={src.max_pages}", "-s", "ROBOTSTXT_OBEY=True",
                   "-s", f"DOWNLOAD_DELAY={rate_limit_delay(src.rate_limit)}", "-s", "CONCURRENT_REQUESTS_PER_DOMAIN=1"]
            for k in SELECTOR_KEYS:
                if (src.config or {}).get(k):
                    cmd += ["-a", f"{k}={src.config[k]}"]
            if src.kind == "playwright":
                cmd += ["-a", "use_playwright=1"]
            proc = run_scrapy_process(cmd, env)
            output = f"{proc.stdout}\n{proc.stderr}"
            if scrapy_run_failed(proc.returncode, output):
                raise RuntimeError((proc.stderr or proc.stdout)[-1000:] or "Scrapy lỗi")
            db.refresh(run)
            collected = run.new_count + run.dup_count + run.error_count
            cleaned = collected
        expects_items = src.connector_type == "rest_api" or src.kind not in ("internal", "manual")
        run.status = completed_run_status(run.error_count, collected, expects_items)
        if run.status == "partial" and not run.message and collected == 0:
            run.message = "Không tìm thấy tin phù hợp; cần kiểm tra lại selector hoặc phản hồi của nguồn."
        src.status = "ok"
    except Exception as exc:
        run.status = "error"
        run.message = str(exc)[:500]
        src.status = "error"
        notify_admins(db, "source_error", f"Nguồn {src.name} thu thập lỗi: {run.message[:120]}", "/admin/nguon", "source_error")
    finally:
        apply_run_health(src, run.status)
        run.finished_at = utcnow()
        src.last_run_at = run.finished_at
        valid = run.new_count
        db.add(PipelineRun(duration_s=int(time.time() - t0), collected=collected, cleaned=cleaned, extracted=cleaned - 0,
                           deduped=valid, scored=valid, indexed=valid, status=run.status))
        db.commit()
        out = {"run_id": run.id, "status": run.status, "new": run.new_count, "dup": run.dup_count, "errors": run.error_count}
        db.close()
    return out


@celery_app.task(name="app.worker.crawl_due_sources")
def crawl_due_sources() -> list[int]:
    db = SessionLocal()
    try:
        due = []
        for s in db.query(CrawlSource).filter(CrawlSource.enabled.is_(True)).all():
            if not s.last_run_at or s.last_run_at < utcnow() - timedelta(minutes=s.frequency_minutes):
                due.append(s.id)
    finally:
        db.close()
    for sid in due:
        crawl_source.delay(sid)
    return due


@celery_app.task(name="app.worker.reindex")
def reindex() -> int:
    db = SessionLocal()
    try:
        return reindex_all(db)
    finally:
        db.close()


@celery_app.task(name="app.worker.recompute_risk")
def recompute_risk() -> int:
    db = SessionLocal()
    try:
        catalog_store.apply(db)
        rows = db.query(Listing).filter(Listing.status.in_(["active", "pending"])).all()
        for l in rows:
            apply_risk(db, l)
        db.commit()
        return len(rows)
    finally:
        db.close()
