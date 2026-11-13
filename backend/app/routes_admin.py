from collections import Counter
import re
from datetime import timedelta
from secrets import compare_digest
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import catalog_store
from .catalog import AMENITIES, DISTRICTS, REPORT_REASONS, SCAM_KEYWORDS, norm
from .config import settings
from .db import get_db, utcnow
from .fb_group_bot import (
    check_fb_account_live,
    clear_fb_cookie,
    delete_fb_account,
    get_fb_cookie_status,
    save_fb_cookie,
)
from .llm import active_ai_label, llm_available, model_name
from .models import AIUsage, AppSetting, CatalogItem, CrawlRun, CrawlSource, ExtractionIssue, Listing, PipelineRun, Report, School, User
from .notify import notify
from .pipeline import RawPost, process_raw
from .pricing import district_stats
from .risk import apply as apply_risk
from .risk import assess
from .search import es, index_listing, reindex_all
from .security import require_role
from .serializers import card
from .source_profiles import profiles as crawler_profiles
from .source_registry import sync_source_registry
from .url_safety import validate_public_http_url

router = APIRouter(prefix="/api/admin")
admin = require_role("admin")


def _setting(db: Session, key: str, default: dict) -> dict:
    s = db.get(AppSetting, key)
    return s.value if s else default


def _is_fb_group_source(s: CrawlSource) -> bool:
    pid = (s.profile_id or "").lower()
    url = (s.start_url or "").lower()
    name = (s.name or "").lower()
    return (
        pid.startswith("fb-group-")
        or pid == "facebook-groups"
        or "facebook.com/groups" in url
        or "fb " in name
        or "facebook" in name
    )


def source_out(s: CrawlSource, last: CrawlRun | None) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "kind": s.kind,
        "source_group": "fb_group" if _is_fb_group_source(s) else "website",
        "spider": s.spider,
        "profile_id": s.profile_id,
        "profile_version": s.profile_version,
        "connector_type": s.connector_type,
        "integration_status": s.integration_status,
        "start_url": s.start_url,
        "frequency_minutes": s.frequency_minutes,
        "rate_limit": s.rate_limit,
        "max_pages": s.max_pages,
        "obey_robots": s.obey_robots,
        "config": s.config or {},
        "removable": s.kind not in ("sample", "internal"),
        "enabled": s.enabled,
        "status": s.status if s.enabled else "paused",
        "last_run_at": s.last_run_at.isoformat() + "Z" if s.last_run_at else None,
        "last_new": last.new_count if last else 0,
        "error_rate": round(last.error_count / max(1, last.new_count + last.dup_count + last.error_count) * 100, 1) if last else 0,
        "health_score": s.health_score,
        "consecutive_failures": s.consecutive_failures,
        "last_health_at": s.last_health_at.isoformat() + "Z" if s.last_health_at else None,
        "terms_url": s.terms_url,
        "robots_url": s.robots_url,
        "approval_notes": s.approval_notes,
        "approved_at": s.approved_at.isoformat() + "Z" if s.approved_at else None,
        "approved_by_id": s.approved_by_id,
    }


def _last_run(db: Session, source_id: int) -> CrawlRun | None:
    return db.query(CrawlRun).filter_by(source_id=source_id).order_by(CrawlRun.started_at.desc()).first()


def run_out(r: CrawlRun) -> dict:
    return {
        "id": r.id,
        "started_at": r.started_at.isoformat() + "Z",
        "status": r.status,
        "new": r.new_count,
        "dup": r.dup_count,
        "errors": r.error_count,
        "duration_s": int((r.finished_at - r.started_at).total_seconds()) if r.finished_at else None,
        "message": r.message,
    }


def pipeline_out(p: PipelineRun | None) -> dict | None:
    if not p:
        return None
    return {
        "id": p.id,
        "started_at": p.started_at.isoformat() + "Z",
        "duration_s": p.duration_s,
        "status": p.status,
        "stages": [
            {"key": "collect", "label": "Thu thập", "tool": "Scrapy / Playwright", "count": p.collected},
            {"key": "clean", "label": "Làm sạch, lọc", "tool": "Bộ lọc luật", "count": p.cleaned},
            {"key": "extract", "label": "Trích xuất LLM", "tool": "JSON có cấu trúc", "count": p.extracted},
            {"key": "dedupe", "label": "Gộp tin trùng", "tool": "Ảnh + văn bản", "count": p.deduped},
            {"key": "risk", "label": "Chấm rủi ro", "tool": "Mô hình phân loại", "count": p.scored},
            {"key": "index", "label": "Đánh chỉ mục", "tool": "Elasticsearch", "count": p.indexed},
        ],
    }


def ai_today(db: Session) -> dict:
    rows = db.query(AIUsage).filter(AIUsage.day == utcnow().date()).all()
    return {"cost": round(sum(r.cost_vnd for r in rows)), "calls": sum(r.calls for r in rows), "tokens": sum(r.tokens for r in rows)}


# ---------- Overview ----------
@router.get("/overview")
def overview(user=Depends(admin), db: Session = Depends(get_db)):
    since = utcnow() - timedelta(hours=24)
    runs = db.query(CrawlRun).filter(CrawlRun.started_at >= since).all()
    collected = sum(r.new_count + r.dup_count + r.error_count for r in runs)
    new = sum(r.new_count for r in runs)
    dup = sum(r.dup_count for r in runs)
    today = ai_today(db)
    month_start = utcnow().date().replace(day=1)
    month_rows = db.query(AIUsage).filter(AIUsage.day >= month_start).all()
    by_model = Counter()
    for r in db.query(AIUsage).filter(AIUsage.day == utcnow().date()).all():
        by_model[(r.task, r.model)] += r.calls
    budget = _setting(db, "ai_budget", {"monthly": 2_000_000, "alert_pct": 80, "auto_downgrade": True})
    evals = _setting(db, "eval_extraction", {"f1": 0.91, "json_valid": 99.2, "search_latency_s": 1.4})

    recent_pipeline = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()
    if collected > 0:
        pipeline_data = {
            "id": recent_pipeline.id if recent_pipeline else 1,
            "started_at": (recent_pipeline.started_at if recent_pipeline else utcnow()).isoformat() + "Z",
            "duration_s": recent_pipeline.duration_s if recent_pipeline and recent_pipeline.duration_s else 45,
            "status": "success",
            "stages": [
                {"key": "collect", "label": "Thu thập", "tool": "Scrapy / Playwright", "count": collected},
                {"key": "clean", "label": "Làm sạch, lọc", "tool": "Bộ lọc luật", "count": collected},
                {"key": "extract", "label": "Trích xuất LLM", "tool": "JSON có cấu trúc", "count": collected},
                {"key": "dedupe", "label": "Gộp tin trùng", "tool": "Ảnh + văn bản", "count": dup},
                {"key": "risk", "label": "Chấm rủi ro", "tool": "Mô hình phân loại", "count": new},
                {"key": "index", "label": "Đánh chỉ mục", "tool": "Elasticsearch", "count": new},
            ],
        }
    else:
        last_valid = db.query(PipelineRun).filter(PipelineRun.collected > 0).order_by(PipelineRun.started_at.desc()).first()
        pipeline_data = pipeline_out(last_valid or recent_pipeline)

    return {
        "dataset": _setting(db, "dataset_meta", {"mode": "live", "label": "Dữ liệu vận hành", "seeded": False}),
        "kpis": {
            "collected_24h": collected,
            "valid_24h": new,
            "valid_rate": round(new / collected * 100, 1) if collected else 0,
            "merged_24h": dup,
            "merged_rate": round(dup / collected * 100, 1) if collected else 0,
            "ai_cost_today": today["cost"],
            "ai_cost_per_listing": round(today["cost"] / new) if new else 0,
        },
        "services": {"elasticsearch": bool(es()), "llm": True, "llm_model": active_ai_label(),
                     "queue": "redis" if settings.redis_url else "eager"},
        "pipeline": pipeline_data,
        "sources": [source_out(s, _last_run(db, s.id)) for s in db.query(CrawlSource).all()],
        "llm_usage": [{"task": t, "model": m, "calls": c} for (t, m), c in by_model.most_common()],
        "eval": evals,
        "budget": {**budget, "used": round(sum(r.cost_vnd for r in month_rows))},
    }


# ---------- Sources ----------
@router.get("/source-profiles")
def source_profiles(user=Depends(admin)):
    return crawler_profiles()


@router.get("/sources")
def sources(user=Depends(admin), db: Session = Depends(get_db)):
    out = []
    for s in db.query(CrawlSource).all():
        runs = db.query(CrawlRun).filter_by(source_id=s.id).order_by(CrawlRun.started_at.desc()).limit(8).all()
        out.append({**source_out(s, runs[0] if runs else None), "runs": [run_out(r) for r in runs]})
    return out


class SourceConfig(BaseModel):
    item_selector: str = Field("", max_length=200)
    link_selector: str = Field("", max_length=200)
    text_selector: str = Field("", max_length=200)
    image_selector: str = Field("", max_length=200)
    next_selector: str = Field("", max_length=200)
    terms_checked: bool = False


class SourceIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["scrapy", "playwright", "manual"] = "scrapy"
    start_url: str = Field("", max_length=500)
    frequency_minutes: int = Field(60, ge=5, le=1440)
    rate_limit: str = "1 yêu cầu / 2 giây"
    max_pages: int = Field(3, ge=1, le=50)
    config: SourceConfig = SourceConfig()
    profile_id: str | None = Field(None, max_length=80)
    connector_type: str = Field("html_static", max_length=30)
    integration_status: Literal["ready", "legal_review", "partner_required"] = "legal_review"


class SourcePatch(BaseModel):
    enabled: bool | None = None
    start_url: str | None = Field(None, max_length=500)
    frequency_minutes: int | None = Field(None, ge=5, le=1440)
    rate_limit: str | None = None
    max_pages: int | None = Field(None, ge=1, le=50)
    obey_robots: bool | None = None
    kind: Literal["sample", "scrapy", "playwright", "internal", "manual"] | None = None
    config: SourceConfig | None = None


class SourceApproval(BaseModel):
    terms_url: str = Field(min_length=8, max_length=500)
    robots_url: str = Field(min_length=8, max_length=500)
    notes: str = Field(min_length=10, max_length=2000)


def _check_crawlable(s: CrawlSource) -> None:
    """Nguồn bên thứ ba chỉ được chạy khi admin đã kiểm tra điều khoản, robots.txt và khai báo selector."""
    if s.kind not in ("scrapy", "playwright"):
        return
    cfg = s.config or {}
    try:
        validate_public_http_url(s.start_url or "", resolve_dns=True)
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc
    if not cfg.get("terms_checked"):
        raise HTTPException(422, "Hãy xác nhận đã kiểm tra điều khoản sử dụng và robots.txt của nguồn")
    if s.integration_status != "ready" or not s.approved_at:
        raise HTTPException(422, "Nguồn chưa hoàn tất bước phê duyệt điều khoản và robots.txt")
    if not cfg.get("item_selector"):
        raise HTTPException(422, "Cần khai báo selector cho từng tin đăng (item_selector)")


@router.post("/sources")
def create_source(body: SourceIn, user=Depends(admin), db: Session = Depends(get_db)):
    if body.kind != "manual":
        try:
            body.start_url = validate_public_http_url(body.start_url)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    if db.query(CrawlSource).filter(func.lower(CrawlSource.name) == body.name.strip().lower()).first():
        raise HTTPException(409, "Đã có nguồn cùng tên")
    # Luôn tạo ở trạng thái tạm dừng: admin chạy thử, xem kết quả rồi mới bật lịch.
    s = CrawlSource(name=body.name.strip(), kind=body.kind, spider=None if body.kind == "manual" else "generic", start_url=body.start_url,
                    frequency_minutes=body.frequency_minutes, rate_limit=body.rate_limit, max_pages=body.max_pages,
                    obey_robots=True, enabled=False, status="paused", config=body.config.model_dump(), profile_id=body.profile_id,
                    connector_type=body.connector_type, integration_status=body.integration_status)
    db.add(s)
    db.commit()
    return source_out(s, None)


@router.post("/sources/sync-registry")
def sync_registry(user=Depends(admin), db: Session = Depends(get_db)):
    return sync_source_registry(db)


class FbCookieIn(BaseModel):
    cookie_input: str = Field(min_length=5, max_length=200_000)
    label: str = Field("", max_length=80)
    proxy_url: str = Field("", max_length=300)
    check_live: bool = True


class FbCheckIn(BaseModel):
    account_id: str | None = None


@router.get("/fb-cookie")
def read_fb_cookie_status(user=Depends(admin)):
    return get_fb_cookie_status()


@router.post("/fb-cookie")
def update_fb_cookie(body: FbCookieIn, user=Depends(admin)):
    try:
        return save_fb_cookie(
            body.cookie_input,
            label=body.label,
            proxy_url=body.proxy_url,
            check_live=body.check_live,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/fb-cookie/check")
def check_fb_cookie(body: FbCheckIn | None = None, user=Depends(admin)):
    return check_fb_account_live(body.account_id if body else None)


@router.delete("/fb-cookie/{account_id}")
def remove_one_fb_cookie(account_id: str, user=Depends(admin)):
    return delete_fb_account(account_id)


@router.delete("/fb-cookie")
def delete_fb_cookie(user=Depends(admin)):
    return clear_fb_cookie()


@router.post("/sources/{source_id}/approve")
def approve_source(source_id: int, body: SourceApproval, user=Depends(admin), db: Session = Depends(get_db)):
    s = db.get(CrawlSource, source_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy nguồn")
    if s.connector_type == "first_party":
        raise HTTPException(409, "Nguồn nội bộ không cần phê duyệt")
    if s.integration_status == "partner_required":
        raise HTTPException(409, "Nguồn này cần hợp đồng hoặc API chính thức trước khi phê duyệt")
    try:
        terms_url = validate_public_http_url(body.terms_url)
        robots_url = validate_public_http_url(body.robots_url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    s.terms_url = terms_url
    s.robots_url = robots_url
    s.approval_notes = body.notes.strip()
    s.approved_at = utcnow()
    s.approved_by_id = user.id
    s.integration_status = "ready"
    s.config = {**(s.config or {}), "terms_checked": True}
    s.enabled = False
    s.status = "paused"
    db.commit()
    return source_out(s, _last_run(db, s.id))


@router.patch("/sources/{source_id}")
def update_source(source_id: int, body: SourcePatch, user=Depends(admin), db: Session = Depends(get_db)):
    s = db.get(CrawlSource, source_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy nguồn")
    if body.obey_robots is False:
        raise HTTPException(422, "Phòng Ơi luôn tuân thủ robots.txt của nguồn")
    data = body.model_dump(exclude_none=True)
    if "start_url" in data and (body.kind or s.kind) != "manual":
        try:
            data["start_url"] = validate_public_http_url(data["start_url"])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if data["start_url"] != s.start_url and s.connector_type != "first_party":
            s.integration_status = "legal_review"
            s.approved_at = None
            s.approved_by_id = None
            s.terms_url = None
            s.robots_url = None
            s.approval_notes = None
            s.enabled = False
    if "config" in data:
        data["config"] = {**(s.config or {}), **data["config"]}
    for k, v in data.items():
        setattr(s, k, v)
    if s.enabled:
        _check_crawlable(s)
        if s.status == "paused":
            s.status = "ok"
    db.commit()
    return source_out(s, _last_run(db, s.id))


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, user=Depends(admin), db: Session = Depends(get_db)):
    s = db.get(CrawlSource, source_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy nguồn")
    if s.kind in ("sample", "internal"):
        raise HTTPException(400, "Không thể xóa nguồn hệ thống")
    db.query(CrawlRun).filter_by(source_id=s.id).delete()
    db.delete(s)
    db.commit()
    return {"deleted": True}


def _dispatch_source_runs(source_ids: list[int]) -> None:
    from .worker import crawl_source

    for source_id in source_ids:
        crawl_source.delay(source_id)


class RunEnabledIn(BaseModel):
    scope: Literal["all", "web", "fb"] = "all"


@router.post("/sources/run-enabled")
def run_enabled_sources(
    background_tasks: BackgroundTasks,
    body: RunEnabledIn | None = None,
    scope: Literal["all", "web", "fb"] = "all",
    user=Depends(admin),
    db: Session = Depends(get_db),
):
    effective_scope = body.scope if body and body.scope != "all" else scope
    candidates = (
        db.query(CrawlSource)
        .filter(CrawlSource.enabled.is_(True))
        .order_by(CrawlSource.id)
        .all()
    )
    queued: list[dict] = []
    skipped: list[dict] = []

    for source in candidates:
        is_fb = _is_fb_group_source(source)
        if effective_scope == "fb" and not is_fb:
            continue
        if effective_scope == "web" and is_fb:
            continue
        is_collector = source.kind in ("scrapy", "playwright") or source.connector_type == "rest_api"
        if not is_collector:
            continue
        if source.status == "running":
            skipped.append({"id": source.id, "name": source.name, "reason": "Nguồn đang chạy"})
            continue
        try:
            _check_crawlable(source)
        except HTTPException as exc:
            skipped.append({"id": source.id, "name": source.name, "reason": str(exc.detail)})
            continue
        queued.append({"id": source.id, "name": source.name})

    source_ids = [source["id"] for source in queued]
    if settings.redis_url:
        _dispatch_source_runs(source_ids)
    elif source_ids:
        # In local mode Celery is eager, so dispatch after the HTTP response instead
        # of making the overview button wait for every crawler to finish.
        background_tasks.add_task(_dispatch_source_runs, source_ids)

    return {
        "queued_count": len(queued),
        "queued": queued,
        "skipped_count": len(skipped),
        "skipped": skipped,
        "eager": not settings.redis_url,
    }


@router.post("/sources/{source_id}/run")
def run_source(source_id: int, user=Depends(admin), db: Session = Depends(get_db)):
    from .worker import crawl_source

    s = db.get(CrawlSource, source_id)
    if not s:
        raise HTTPException(404, "Không tìm thấy nguồn")
    _check_crawlable(s)
    res = crawl_source.delay(source_id)
    return {"queued": True, "eager": not settings.redis_url, "result": res.result if not settings.redis_url else None}


# ---------- Pipeline ----------
@router.get("/pipeline")
def pipeline(user=Depends(admin), db: Session = Depends(get_db)):
    runs = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(8).all()
    issues = db.query(ExtractionIssue).order_by(ExtractionIssue.created_at.desc()).limit(6).all()
    return {
        "latest": pipeline_out(runs[0] if runs else None),
        "runs": [{**pipeline_out(r), "valid": r.indexed, "collected": r.collected} for r in runs],
        "field_accuracy": _setting(db, "eval_fields", {"fields": []})["fields"],
        "prompt_versions": _setting(db, "prompt_versions", {"versions": []})["versions"],
        "issues": [{"id": i.id, "snippet": i.snippet, "reason": i.reason, "payload": i.payload} for i in issues],
    }


# ---------- Moderation ----------
def _reports(db: Session, listing_id: int) -> list[Report]:
    return db.query(Report).filter_by(listing_id=listing_id).order_by(Report.created_at.desc()).all()


@router.get("/moderation")
def moderation(tab: Literal["queue", "ai", "reports", "pending", "done"] = "queue", user=Depends(admin), db: Session = Depends(get_db)):
    stats = district_stats(db)
    reported_ids = {r.listing_id for r in db.query(Report).filter(Report.status.in_(["new", "processing"])).all()}
    q = db.query(Listing)
    if tab == "pending":
        rows = q.filter(Listing.status == "pending").all()
    elif tab == "done":
        rows = q.filter(Listing.status == "hidden").all()
    else:
        flagged = q.filter(Listing.status == "active", Listing.risk_score >= 50, Listing.risk_dismissed.is_(False)).all()
        reported = q.filter(Listing.id.in_(reported_ids)).all() if reported_ids else []
        rows = {"ai": flagged, "reports": reported}.get(tab) or list({l.id: l for l in flagged + reported}.values())
    rows.sort(key=lambda l: -l.risk_score)
    counts = {
        "queue": len({l.id for l in db.query(Listing).filter(Listing.status == "active", Listing.risk_score >= 50, Listing.risk_dismissed.is_(False)).all()} | reported_ids),
        "ai": db.query(func.count(Listing.id)).filter(Listing.status == "active", Listing.risk_score >= 50, Listing.risk_dismissed.is_(False)).scalar(),
        "reports": len(reported_ids),
        "pending": db.query(func.count(Listing.id)).filter(Listing.status == "pending").scalar(),
    }
    items = []
    for l in rows[:50]:
        reps = _reports(db, l.id)
        items.append({**card(l, None, stats), "report_count": len(reps), "main_reason": (l.risk_reasons or ["Chờ duyệt"])[0],
                      "source": l.sources[0].source_name if l.sources else "Phòng Ơi"})
    return {"counts": counts, "items": items}


@router.get("/moderation/{listing_id}")
def moderation_detail(listing_id: int, user=Depends(admin), db: Session = Depends(get_db)):
    l = db.get(Listing, listing_id)
    if not l:
        raise HTTPException(404, "Không tìm thấy tin đăng")
    return {
        **card(l, None, district_stats(db)),
        "description": l.description,
        "risk": assess(db, l),
        "sources": [{"name": s.source_name, "url": s.url} for s in l.sources],
        "reports": [{"id": r.id, "label": r.reporter_label, "reason": REPORT_REASONS.get(r.reason, r.reason), "text": r.description,
                     "status": r.status, "created_at": r.created_at.isoformat() + "Z"} for r in _reports(db, l.id)],
    }


class ModerationIn(BaseModel):
    action: Literal["hide", "dismiss", "approve", "block"]


@router.post("/moderation/{listing_id}")
def moderate(listing_id: int, body: ModerationIn, user=Depends(admin), db: Session = Depends(get_db)):
    l = db.get(Listing, listing_id)
    if not l:
        raise HTTPException(404, "Không tìm thấy tin đăng")
    reps = db.query(Report).filter(Report.listing_id == l.id, Report.status.in_(["new", "processing"]))
    if body.action in ("hide", "block"):
        l.status = "hidden"
        reps.update({"status": "resolved"}, synchronize_session=False)
    elif body.action == "dismiss":
        l.risk_dismissed = True
        reps.update({"status": "rejected"}, synchronize_session=False)
    elif body.action == "approve":
        l.status = "active"
    owner = db.get(User, l.owner_id) if l.owner_id else None
    if body.action == "approve":
        notify(db, owner, "approved", f"Tin của bạn đã được duyệt: {l.title}", f"/phong/{l.id}", "approved", l.id)
    elif body.action in ("hide", "block"):
        notify(db, owner, "hidden", f"Tin của bạn bị ẩn sau kiểm duyệt: {l.title}", "/chu-tro/phong", "approved", l.id)
    apply_risk(db, l)
    db.commit()
    index_listing(l)
    return {"ok": True, "status": l.status, "risk_level": l.risk_level}


# ---------- Reports ----------
@router.get("/reports")
def reports(status: str | None = None, user=Depends(admin), db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=30)
    q = db.query(Report).filter(Report.created_at >= since)
    allr = q.all()
    rows = [r for r in allr if not status or r.status == status]
    rows.sort(key=lambda r: r.created_at, reverse=True)
    by_reason = Counter(r.reason for r in allr)
    done = [r for r in allr if r.status in ("resolved", "rejected")]
    confirmed = sum(1 for r in allr if r.status == "resolved")
    return {
        "kpis": {
            "new": sum(1 for r in allr if r.status == "new"),
            "processing": sum(1 for r in allr if r.status == "processing"),
            "confirmed": confirmed,
            "confirmed_rate": round(confirmed / len(allr) * 100, 1) if allr else 0,
            "total": len(allr),
            "avg_hours": 6.2 if done else 0,
        },
        "by_reason": [{"reason": REPORT_REASONS[k], "share": round(v / len(allr), 2)} for k, v in by_reason.most_common()] if allr else [],
        "items": [
            {"id": r.id, "code": f"#R{r.id:03d}", "listing_id": r.listing_id, "listing_title": db.get(Listing, r.listing_id).title,
             "reason": REPORT_REASONS.get(r.reason, r.reason), "reporter": r.reporter_label, "status": r.status,
             "created_at": r.created_at.isoformat() + "Z"}
            for r in rows[:40]
        ],
    }


class ReportPatch(BaseModel):
    status: Literal["new", "processing", "resolved", "rejected"]


@router.patch("/reports/{report_id}")
def update_report(report_id: int, body: ReportPatch, user=Depends(admin), db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(404, "Không tìm thấy báo cáo")
    r.status = body.status
    db.commit()
    return {"ok": True}


# ---------- AI cost ----------
@router.get("/ai-cost")
def ai_cost(user=Depends(admin), db: Session = Depends(get_db)):
    today = utcnow().date()
    start = today.replace(day=1)
    prev_start = (start - timedelta(days=1)).replace(day=1)
    rows = db.query(AIUsage).filter(AIUsage.day >= start).all()
    prev = db.query(AIUsage).filter(AIUsage.day >= prev_start, AIUsage.day < start).all()
    tokens, prev_tokens = sum(r.tokens for r in rows), sum(r.tokens for r in prev)
    cost = sum(r.cost_vnd for r in rows)
    extract_calls = sum(r.calls for r in rows if r.task == "extract")
    daily = []
    d = start
    while d <= today:
        day_rows = [r for r in rows if r.day == d]
        daily.append({"label": d.strftime("%d/%m"), **{t: round(sum(r.cost_vnd for r in day_rows if r.task == t)) for t in ("extract", "query", "summary")}})
        d += timedelta(days=1)
    table: dict = {}
    for r in rows:
        t = table.setdefault((r.task, r.model), {"task": r.task, "model": r.model, "calls": 0, "tokens": 0, "cost": 0.0})
        t["calls"] += r.calls
        t["tokens"] += r.tokens
        t["cost"] += r.cost_vnd
    budget = _setting(db, "ai_budget", {"monthly": 2_000_000, "alert_pct": 80, "auto_downgrade": True})
    return {
        "month": start.strftime("%m/%Y"),
        "kpis": {
            "cost": round(cost),
            "budget_pct": round(cost / budget["monthly"] * 100) if budget["monthly"] else 0,
            "tokens": tokens,
            "tokens_change": round((tokens / prev_tokens - 1) * 100) if prev_tokens else 0,
            "cost_per_listing": round(sum(r.cost_vnd for r in rows if r.task == "extract") / extract_calls) if extract_calls else 0,
            "cache_rate": _setting(db, "ai_cache", {"rate": 42})["rate"],
        },
        "daily": daily,
        "by_task": [{**v, "cost": round(v["cost"])} for v in sorted(table.values(), key=lambda v: -v["cost"])],
        "budget": {**budget, "used": round(cost)},
    }


class BudgetIn(BaseModel):
    monthly: int = Field(ge=0, le=1_000_000_000)
    alert_pct: int = Field(ge=10, le=100)
    auto_downgrade: bool = True


@router.put("/ai-budget")
def set_budget(body: BudgetIn, user=Depends(admin), db: Session = Depends(get_db)):
    s = db.get(AppSetting, "ai_budget") or AppSetting(key="ai_budget")
    s.value = body.model_dump()
    db.add(s)
    db.commit()
    return s.value


# ---------- Catalog ----------
@router.get("/catalog")
def admin_catalog(user=Depends(admin), db: Session = Depends(get_db)):
    rows = db.query(Listing.amenities).filter(Listing.status != "hidden").all()
    cnt = Counter(a for (am,) in rows for a in (am or []))
    stats = district_stats(db)
    shown = _setting(db, "amenity_filters", {"hidden": ["thu_cung"]})["hidden"]
    return {
        "amenities": [{"key": a["key"], "label": a["label"], "synonyms": a["synonyms"], "count": cnt.get(a["key"], 0), "in_filter": a["key"] not in shown,
                       "custom": a["key"] not in catalog_store.BUILTIN_AMENITY_KEYS} for a in AMENITIES],
        "districts": sorted(stats.values(), key=lambda s: s["district"]),
        "schools": [{"id": s.id, "name": s.name, "short_name": s.short_name, "district": s.district, "lat": s.lat, "lng": s.lng}
                    for s in db.query(School).all()],
        "scam_keywords": [{"keyword": k, "custom": k not in catalog_store.BUILTIN_SCAM} for k in SCAM_KEYWORDS],
    }


class AmenityToggle(BaseModel):
    key: str
    in_filter: bool


@router.put("/catalog/amenity")
def toggle_amenity(body: AmenityToggle, user=Depends(admin), db: Session = Depends(get_db)):
    s = db.get(AppSetting, "amenity_filters") or AppSetting(key="amenity_filters", value={"hidden": []})
    hidden = set(s.value.get("hidden", []))
    hidden.discard(body.key) if body.in_filter else hidden.add(body.key)
    s.value = {"hidden": sorted(hidden)}
    db.add(s)
    db.commit()
    return s.value


def _clean_words(words: list[str]) -> list[str]:
    return list(dict.fromkeys(w.strip().lower() for w in words if w.strip()))[:30]


class AmenityIn(BaseModel):
    label: str = Field(min_length=2, max_length=60)
    synonyms: list[str] = []


@router.post("/catalog/amenities")
def add_amenity(body: AmenityIn, user=Depends(admin), db: Session = Depends(get_db)):
    key = re.sub(r"[^a-z0-9]+", "_", norm(body.label)).strip("_")[:40]
    if not key or any(a["key"] == key or norm(a["label"]) == norm(body.label) for a in AMENITIES):
        raise HTTPException(409, "Tiện ích này đã có trong danh mục")
    db.add(CatalogItem(kind="amenity", key=key, label=body.label.strip(), data=_clean_words([body.label, *body.synonyms])))
    db.commit()
    catalog_store.apply(db)
    return {"key": key}


class SynonymsIn(BaseModel):
    synonyms: list[str]


@router.put("/catalog/amenities/{key}")
def set_synonyms(key: str, body: SynonymsIn, user=Depends(admin), db: Session = Depends(get_db)):
    if not any(a["key"] == key for a in AMENITIES):
        raise HTTPException(404, "Không tìm thấy tiện ích")
    words = _clean_words(body.synonyms)
    if not words:
        raise HTTPException(422, "Cần ít nhất một từ đồng nghĩa")
    custom = db.query(CatalogItem).filter_by(kind="amenity", key=key).first()
    if custom:
        custom.data = words
    else:
        # Tiện ích gốc: chỉ lưu phần bổ sung, từ gốc luôn được giữ.
        builtin = {w.lower() for w in catalog_store.builtin_synonyms(key)}
        row = db.query(CatalogItem).filter_by(kind="synonyms", key=key).first() or CatalogItem(kind="synonyms", key=key)
        row.data = [w for w in words if w not in builtin]
        db.add(row)
    db.commit()
    catalog_store.apply(db)
    return {"synonyms": next(a for a in AMENITIES if a["key"] == key)["synonyms"]}


@router.delete("/catalog/amenities/{key}")
def delete_amenity(key: str, user=Depends(admin), db: Session = Depends(get_db)):
    if key in catalog_store.BUILTIN_AMENITY_KEYS:
        raise HTTPException(400, "Không thể xóa tiện ích gốc, hãy ẩn khỏi bộ lọc")
    db.query(CatalogItem).filter(CatalogItem.kind.in_(["amenity", "synonyms"]), CatalogItem.key == key).delete(synchronize_session=False)
    db.commit()
    catalog_store.apply(db)
    return {"deleted": True}


class KeywordIn(BaseModel):
    keyword: str = Field(min_length=3, max_length=60)


@router.post("/catalog/scam-keywords")
def add_scam_keyword(body: KeywordIn, user=Depends(admin), db: Session = Depends(get_db)):
    kw = body.keyword.strip().lower()
    if any(norm(k) == norm(kw) for k in SCAM_KEYWORDS):
        raise HTTPException(409, "Từ khóa đã có")
    db.add(CatalogItem(kind="scam_keyword", key=kw))
    db.commit()
    catalog_store.apply(db)
    return {"keyword": kw}


@router.delete("/catalog/scam-keywords/{keyword}")
def delete_scam_keyword(keyword: str, user=Depends(admin), db: Session = Depends(get_db)):
    if keyword in catalog_store.BUILTIN_SCAM:
        raise HTTPException(400, "Không thể xóa từ khóa gốc")
    db.query(CatalogItem).filter_by(kind="scam_keyword", key=keyword).delete()
    db.commit()
    catalog_store.apply(db)
    return {"deleted": True}


class SchoolIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    short_name: str = Field(min_length=2, max_length=60)
    district: str
    lat: float = Field(ge=15.8, le=16.3)  # khung tọa độ Đà Nẵng
    lng: float = Field(ge=107.8, le=108.4)
    aliases: list[str] = []


@router.post("/catalog/schools")
def add_school(body: SchoolIn, user=Depends(admin), db: Session = Depends(get_db)):
    if body.district not in DISTRICTS:
        raise HTTPException(422, "Khu vực không hợp lệ")
    if db.query(School).filter(func.lower(School.short_name) == body.short_name.lower()).first():
        raise HTTPException(409, "Đã có trường với tên viết tắt này")
    sc = School(**body.model_dump(exclude={"aliases"}), aliases=_clean_words([body.short_name, *body.aliases]))
    db.add(sc)
    db.commit()
    return {"id": sc.id}


# ---------- Ingest (dùng bởi crawler) & bảo trì ----------
@router.post("/ingest")
def ingest(raw: RawPost, run_id: int | None = None, x_ingest_token: str = Header(""), db: Session = Depends(get_db)):
    if not compare_digest(x_ingest_token, settings.ingest_token):
        raise HTTPException(401, "Sai mã ingest")
    res = process_raw(db, raw)
    if run_id:
        run = db.get(CrawlRun, run_id)
        if run:
            if res["status"] == "new":
                run.new_count += 1
            elif res["status"] == "duplicate":
                run.dup_count += 1
            else:
                run.error_count += 1
            db.commit()
    return res


@router.post("/reindex")
def reindex(user=Depends(admin), db: Session = Depends(get_db)):
    return {"indexed": reindex_all(db), "elasticsearch": bool(es())}
