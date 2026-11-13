import hashlib
import secrets
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .catalog import AMENITIES, DISTRICTS, LANDMARKS, REPORT_REASONS, ROOM_TYPES
from .db import get_db, utcnow
from .extract import build_ai_insights, build_enriched_ai_summary
from .geo import haversine_km, travel_text
from .config import settings
from .mailer import send_mail
from .models import CrawlSource, Listing, ListingStat, NeedsProfile, PasswordReset, SavedListing, School, SearchLog, User
from .notify import notify
from .pricing import city_median, district_stats, estimate, monthly_cost, price_position, price_trend
from .query_parser import SearchFilters, chips, parse_query
from .recommend import match
from .risk import assess
from .search import run_search
from .security import create_token, current_user, current_user_optional, hash_password, verify_password
from .serializers import card, normalize_ai_summary

router = APIRouter(prefix="/api")


def user_out(u: User) -> dict:
    initials = "".join(w[0] for w in u.full_name.split()[-2:]).upper()
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "initials": initials,
        "role": u.role,
        "phone": u.phone,
        "school_id": u.school_id,
        "bio": u.bio,
        "email_verified": u.email_verified,
        "phone_verified": u.phone_verified,
        "address_verified": u.address_verified,
        "id_verification": u.id_verification,
        "personalize": u.personalize,
        "created_at": u.created_at.isoformat() + "Z",
    }


def filters_from_profile(p: NeedsProfile | None) -> SearchFilters:
    if not p:
        return SearchFilters()
    return SearchFilters(
        budget_min=p.budget_min,
        budget_max=p.budget_max,
        school_id=p.school_id,
        max_distance_km=p.max_distance_km,
        districts=p.districts or [],
        room_types=p.room_types or [],
        amenities=p.amenities or [],
        max_people=p.max_people,
    )


# ---------- Auth ----------
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Literal["student", "landlord"] = "student"
    school_id: int | None = None


class LoginIn(BaseModel):
    email: str
    password: str


@router.post("/auth/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "Email này đã được đăng ký")
    u = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name.strip(), role=body.role, school_id=body.school_id)
    db.add(u)
    db.commit()
    return {"token": create_token(u), "user": user_out(u)}


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=body.email.lower().strip()).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    return {"token": create_token(u), "user": user_out(u)}


@router.get("/auth/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


class ForgotIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


@router.post("/auth/forgot")
def forgot_password(body: ForgotIn, db: Session = Depends(get_db)):
    # Luôn trả cùng một thông điệp để không lộ email nào đã đăng ký.
    out = {"ok": True, "message": "Nếu email đã đăng ký, liên kết đặt lại mật khẩu sẽ được gửi trong vài phút."}
    u = db.query(User).filter_by(email=body.email.lower().strip()).first()
    if not u:
        return out
    token = secrets.token_urlsafe(32)
    db.add(PasswordReset(user_id=u.id, token_hash=_hash_token(token), expires_at=utcnow() + timedelta(minutes=30)))
    db.commit()
    url = f"{settings.app_url}/dat-lai-mat-khau?token={token}"
    sent = send_mail(u.email, "Đặt lại mật khẩu Phòng Ơi",
                     f"Chào {u.full_name},\n\nBấm vào liên kết sau để đặt lại mật khẩu (hiệu lực 30 phút):\n{url}\n\nNếu bạn không yêu cầu, hãy bỏ qua email này.")
    if not sent and settings.app_env == "development":
        out["dev_reset_url"] = url  # chỉ để demo khi chưa cấu hình SMTP; production không bao giờ trả về
    return out


@router.post("/auth/reset")
def reset_password(body: ResetIn, db: Session = Depends(get_db)):
    r = db.query(PasswordReset).filter_by(token_hash=_hash_token(body.token), used=False).first()
    if not r or r.expires_at < utcnow():
        raise HTTPException(400, "Liên kết đặt lại đã hết hạn hoặc không hợp lệ")
    u = db.get(User, r.user_id)
    u.password_hash = hash_password(body.password)
    db.query(PasswordReset).filter_by(user_id=u.id, used=False).update({"used": True})
    db.commit()
    return {"token": create_token(u), "user": user_out(u)}


@router.put("/me/password")
def change_password(body: ChangePasswordIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Mật khẩu hiện tại không đúng")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}


# ---------- Catalog & home ----------
@router.get("/catalog")
def catalog(db: Session = Depends(get_db)):
    return {
        "amenities": [{"key": a["key"], "label": a["label"]} for a in AMENITIES],
        "districts": list(DISTRICTS),
        "schools": [{"id": s.id, "name": s.name, "short_name": s.short_name, "district": s.district} for s in db.query(School).all()],
        "room_types": [{"key": k, "label": v} for k, v in ROOM_TYPES.items()],
        "report_reasons": [{"key": k, "label": v} for k, v in REPORT_REASONS.items()],
    }


@router.get("/home")
def home(db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    week = utcnow() - timedelta(days=7)
    stats = district_stats(db)
    profile = db.get(NeedsProfile, user.id) if user else None
    f = filters_from_profile(profile) if profile else SearchFilters(school_id=1, max_distance_km=3, budget_max=2_800_000)
    featured = run_search(db, f, page_size=4)
    school = db.get(School, f.school_id) if f.school_id else None
    return {
        "active_listings": db.query(func.count(Listing.id)).filter(Listing.status == "active").scalar(),
        "new_this_week": db.query(func.count(Listing.id)).filter(Listing.posted_at >= week).scalar(),
        "sources": db.query(func.count(CrawlSource.id)).filter(CrawlSource.enabled.is_(True)).scalar(),
        "hidden_risky": db.query(func.count(Listing.id)).filter(Listing.risk_level == "high").scalar(),
        "city_median": city_median(db),
        "school": school.short_name if school else None,
        "featured": featured["items"],
        "districts": sorted(stats.values(), key=lambda s: s["median"]),
        "personalized": bool(profile),
    }


# ---------- Search ----------
class ParseIn(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class SearchIn(BaseModel):
    query: str | None = Field(None, max_length=500)
    filters: SearchFilters | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(12, ge=1, le=48)


@router.post("/search/parse")
def search_parse(body: ParseIn, db: Session = Depends(get_db)):
    f, c, engine = parse_query(body.query, db)
    return {"filters": f.model_dump(), "chips": c, "engine": engine}


@router.post("/search")
def search(body: SearchIn, db: Session = Depends(get_db)):
    engine = "manual"
    if body.filters is not None:
        f = body.filters
    elif body.query:
        f, _, engine = parse_query(body.query, db)
    else:
        f = SearchFilters()
    res = run_search(db, f, body.page, body.page_size)
    if body.query and body.page == 1:
        db.add(SearchLog(query=body.query, filters=f.model_dump(), engine=engine, result_count=res["total"]))
        db.commit()
    res.update(filters=f.model_dump(), chips=chips(f, db.query(School).all()), parse_engine=engine)
    return res


# ---------- Listing detail ----------
def _source_platform(name: str) -> str:
    n = (name or "").strip().lower()
    if "fb" in n or "facebook" in n:
        return "facebook"
    return n


def deduplicate_sources(sources: list) -> list:
    """Giữ bài đăng gốc chính xác và chỉ gộp thêm khi thực sự cùng một phòng đăng chéo nền tảng."""
    import re
    from .catalog import norm
    from .extract import strip_crawled_noise

    items = list(sources or [])
    if not items:
        return []

    primary = items[0]
    unique = [primary]
    seen_urls = {((getattr(primary, "url", None) or "").split("?")[0].rstrip("/").lower())}
    seen_platforms = {_source_platform(getattr(primary, "source_name", ""))}
    p_text = strip_crawled_noise(getattr(primary, "raw_text", "") or "")
    p_tokens = {w for w in norm(p_text[:250]).split() if len(w) > 2}
    p_fb_id = None
    if m := re.search(r"/posts/(\d+)", getattr(primary, "url", "") or ""):
        p_fb_id = m.group(1)

    for s in items[1:]:
        raw_url = getattr(s, "url", None) or ""
        norm_url = raw_url.split("?")[0].rstrip("/").lower()
        plat = _source_platform(getattr(s, "source_name", ""))
        if not norm_url or norm_url in seen_urls or plat in seen_platforms:
            continue
        if p_fb_id and f"/posts/{p_fb_id}" in norm_url:
            continue
        s_text = strip_crawled_noise(getattr(s, "raw_text", "") or "")
        s_tokens = {w for w in norm(s_text[:250]).split() if len(w) > 2}
        # Nếu nội dung đầu bài khác hoàn toàn (< 55% từ khóa chung) thì là tin khác bị gộp nhầm trước đây
        if p_tokens and s_tokens and (len(p_tokens & s_tokens) / max(1, len(p_tokens | s_tokens))) < 0.55:
            continue
        seen_urls.add(norm_url)
        seen_platforms.add(plat)
        unique.append(s)
    return unique


def _similarity_score(target: Listing, cand: Listing) -> float:
    score = 0.0
    student_types = {"phong_tro", "o_ghep"}
    if cand.room_type == target.room_type:
        score += 35.0
    elif (cand.room_type in student_types) == (target.room_type in student_types):
        score += 16.0

    if target.lat and target.lng and cand.lat and cand.lng:
        km = haversine_km(target.lat, target.lng, cand.lat, cand.lng)
        score += max(0.0, 30.0 * (1.0 - km / 6.0))
    if cand.district == target.district:
        score += 10.0
    if target.street and cand.street and cand.street == target.street:
        score += 6.0

    rel_price = abs((cand.price or 0) - (target.price or 0)) / max(target.price or 1, 500_000)
    score += max(0.0, 20.0 * (1.0 - rel_price / 0.45))

    t_am = set(target.amenities or [])
    c_am = set(cand.amenities or [])
    if t_am or c_am:
        score += 8.0 * (len(t_am & c_am) / max(1, len(t_am | c_am)))

    if cand.images:
        score += 4.0
    score += min(3.0, (cand.quality_score or 7.0) * 0.3)
    return score


def rank_similar_listings(target: Listing, candidates: list[Listing]) -> list[Listing]:
    """Xếp hạng danh sách phòng tương tự theo đa tiêu chí: loại phòng, khoảng cách Haversine, giá, tiện ích & chất lượng."""
    return sorted(
        (c for c in candidates if c.id != target.id),
        key=lambda c: (-_similarity_score(target, c), abs((c.price or 0) - (target.price or 0))),
    )


@router.get("/listings/{listing_id}")
def listing_detail(listing_id: int, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    l = db.get(Listing, listing_id)
    if not l or l.status == "hidden" and not (user and user.role == "admin"):
        raise HTTPException(404, "Không tìm thấy tin đăng")
    stats = district_stats(db)
    profile = db.get(NeedsProfile, user.id) if user else None
    f = filters_from_profile(profile)
    all_schools = db.query(School).all()
    nearest_school = (
        min(all_schools, key=lambda s: haversine_km(l.lat, l.lng, s.lat, s.lng))
        if (l.lat and l.lng and all_schools)
        else None
    )
    school = db.get(School, f.school_id or (user.school_id if user else None)) if (f.school_id or (user and user.school_id)) else (nearest_school or db.get(School, 1))
    m = match(l, f, school, stats)
    schools = sorted(
        ({"name": s.name, "km": haversine_km(l.lat, l.lng, s.lat, s.lng), "kind": "school"} for s in all_schools), key=lambda x: x["km"]
    )[:2]
    marks = sorted(({"name": p["name"], "km": haversine_km(l.lat, l.lng, p["lat"], p["lng"]), "kind": "place"} for p in LANDMARKS), key=lambda x: x["km"])[:2]
    similar_q = (
        db.query(Listing)
        .filter(Listing.id != l.id, Listing.status == "active", Listing.risk_level != "high")
        .filter(Listing.price.between(int(l.price * 0.65), int(l.price * 1.35)))
        .limit(80)
        .all()
    )
    top_similar = rank_similar_listings(l, similar_q)[:4]
    similar = [card(s, match(s, f, school, stats), stats) for s in top_similar]
    owner = db.get(User, l.owner_id) if l.owner_id else None
    saved = bool(user and db.get(SavedListing, (user.id, l.id)))
    nearby_list = [{"name": x["name"], "kind": x["kind"], "km": round(x["km"], 2), "text": travel_text(x["km"])} for x in schools + marks]
    risk_info = assess(db, l)
    pa_info = price_position(db, l)
    base_summary = normalize_ai_summary(l.ai_summary)
    unique_sources = deduplicate_sources(l.sources)
    card_payload = card(l, m, stats)
    card_payload["source_count"] = max(1, len(unique_sources))
    return {
        **card_payload,
        "description": l.description,
        "ai_summary": build_enriched_ai_summary(l, pa_info, nearby_list, risk_info, base_summary),
        "ai_insights": build_ai_insights(l, pa_info, nearby_list, risk_info),
        "deposit_months": l.deposit_months,
        "electricity_price": l.electricity_price,
        "water_price": l.water_price,
        "risk": risk_info,
        "price": l.price,
        "price_analysis": pa_info,
        "monthly_cost": monthly_cost(l),
        "nearby": nearby_list,
        "school": {"name": school.short_name, "lat": school.lat, "lng": school.lng} if school else None,
        "sources": [{"name": s.source_name, "url": s.url, "posted_at": s.posted_at.isoformat() + "Z"} for s in unique_sources],
        "similar": similar,
        "owner": {"name": owner.full_name, "verified": owner.phone_verified} if owner else None,
        "saved": saved,
        "personalized": bool(profile),
    }


class EventIn(BaseModel):
    kind: Literal["view", "contact", "impression"]


@router.post("/listings/{listing_id}/event")
def listing_event(listing_id: int, body: EventIn, db: Session = Depends(get_db)):
    l = db.get(Listing, listing_id)
    if not l:
        raise HTTPException(404, "Không tìm thấy tin đăng")
    today = utcnow().date()
    st = db.query(ListingStat).filter_by(listing_id=l.id, day=today).first()
    if not st:
        st = ListingStat(listing_id=l.id, day=today, impressions=0, views=0, contacts=0, saves=0)
        db.add(st)
    if body.kind == "view":
        l.views += 1
        st.views += 1
    elif body.kind == "contact":
        l.contacts += 1
        st.contacts += 1
        if l.owner_id:
            notify(db, db.get(User, l.owner_id), "contact", f"Có sinh viên vừa xem bài gốc {l.title}", "/chu-tro/thong-ke", "contact", l.id)
    else:
        st.impressions += 1
    db.commit()
    return {"ok": True}


# ---------- Market ----------
class EstimateIn(BaseModel):
    district: str
    area: float | None = Field(None, ge=5, le=300)
    amenities: list[str] = []
    room_type: str = "phong_tro"


@router.get("/market/overview")
def market_overview(db: Session = Depends(get_db)):
    stats = sorted(district_stats(db).values(), key=lambda s: s["median"])
    trend = price_trend(db)
    vals = [t["median"] for t in trend if t["median"]]
    total = db.query(func.count(Listing.id)).filter(Listing.status == "active").scalar()
    today_new = db.query(func.count(Listing.id)).filter(Listing.posted_at >= utcnow() - timedelta(days=1)).scalar()
    return {
        "city_median": city_median(db),
        "change_30d": round((vals[-1] / vals[-2] - 1) * 100, 1) if len(vals) >= 2 else 0,
        "active": total,
        "new_today": today_new,
        "cheapest": stats[0],
        "priciest": stats[-1],
        "districts": stats,
        "trend": trend,
        "peak_label": "Mùa nhập học",
    }


@router.post("/market/estimate")
def market_estimate(body: EstimateIn, db: Session = Depends(get_db)):
    if body.district not in DISTRICTS:
        raise HTTPException(422, "Khu vực không hợp lệ")
    return estimate(db, body.district, body.area, body.amenities, body.room_type)
