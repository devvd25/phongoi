import uuid
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .catalog import AMENITY_KEYS, AMENITY_LABEL, DISTRICTS, ROOM_TYPES
from .db import get_db, utcnow
from .extract import extract
from .geo import approx_location
from .models import Listing, ListingStat, Report, SearchLog, User
from .money import short_vnd
from .notify import notify_admins, notify_savers
from .pricing import district_stats, estimate
from .risk import apply as apply_risk
from .risk import quality
from .routes_public import user_out
from .search import index_listing
from .security import require_role
from .serializers import card

router = APIRouter(prefix="/api/landlord")
landlord = require_role("landlord", "admin")
UPLOAD_DIR = Path("uploads")
WEEKDAY = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def _rooms(db: Session, user: User) -> list[Listing]:
    return db.query(Listing).filter(Listing.owner_id == user.id).order_by(Listing.title).all()


def _sum_stats(db: Session, ids: list[int], start, end) -> dict:
    if not ids:
        return {"impressions": 0, "views": 0, "contacts": 0, "saves": 0}
    r = (
        db.query(func.sum(ListingStat.impressions), func.sum(ListingStat.views), func.sum(ListingStat.contacts), func.sum(ListingStat.saves))
        .filter(ListingStat.listing_id.in_(ids), ListingStat.day >= start, ListingStat.day < end)
        .one()
    )
    return {"impressions": r[0] or 0, "views": r[1] or 0, "contacts": r[2] or 0, "saves": r[3] or 0}


def _pct(a: int, b: int) -> int:
    return round((a / b - 1) * 100) if b else 0


def room_out(db: Session, l: Listing, stats: dict) -> dict:
    status_label = {"active": "Còn trống", "rented": "Đã cho thuê", "pending": "Chờ duyệt", "hidden": "Đã ẩn"}[l.status]
    if l.status == "rented" and l.available_from:
        status_label = f"Sắp trống {l.available_from:%d/%m}"
    tone = {"active": "Success", "rented": "Neutral", "pending": "Info", "hidden": "Danger"}[l.status]
    if l.status == "rented" and l.available_from:
        tone = "Warning"
    return {**card(l, None, stats), "status_label": status_label, "status_tone": tone, "views": l.views, "contacts": l.contacts}


@router.get("/dashboard")
def dashboard(user: User = Depends(landlord), db: Session = Depends(get_db)):
    rooms = _rooms(db, user)
    ids = [r.id for r in rooms]
    today = utcnow().date()
    week = _sum_stats(db, ids, today - timedelta(days=6), today + timedelta(days=1))
    prev = _sum_stats(db, ids, today - timedelta(days=13), today - timedelta(days=6))
    stats = district_stats(db)
    series = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        s = _sum_stats(db, ids, d, d + timedelta(days=1))
        series.append({"label": WEEKDAY[d.weekday()], "views": s["views"]})
    suggestions = []
    for r in rooms:
        name = r.title.split(" · ")[0]
        if r.status == "active":
            med = stats.get(r.district, {}).get("median")
            if med and r.price > med * 1.1:
                est = estimate(db, r.district, r.area, r.amenities or [], r.room_type)
                suggestions.append({"kind": "price", "listing_id": r.id, "title": f"{name} cao hơn {round((r.price / med - 1) * 100)}% so với khu vực",
                                    "text": f"Đề xuất {short_vnd(est['mid'])} để cho thuê nhanh hơn", "action": "Áp dụng giá", "suggested_price": est["mid"]})
            days = (utcnow() - r.posted_at).days
            if days > 14:
                suggestions.append({"kind": "stale", "listing_id": r.id, "title": f"{name} trống {days} ngày",
                                    "text": "Bổ sung tiện ích hoặc làm mới tin để lên đầu kết quả", "action": "Làm mới tin"})
        if r.status in ("active", "pending") and len(r.images or []) < 5:
            suggestions.append({"kind": "photos", "listing_id": r.id, "title": f"{name} mới có {len(r.images or [])} ảnh",
                                "text": "Thêm ít nhất 5 ảnh để điểm chất lượng đạt 8+", "action": "Thêm ảnh"})
    rented = sum(1 for r in rooms if r.status == "rented")
    return {
        "user": user_out(user),
        "kpis": {
            "rented": rented,
            "total": len(rooms),
            "occupancy": round(rented / len(rooms) * 100) if rooms else 0,
            "available": sum(1 for r in rooms if r.status == "active"),
            "views_week": week["views"],
            "views_change": _pct(week["views"], prev["views"]),
            "contacts_week": week["contacts"],
            "conversion": round(week["contacts"] / week["views"] * 100, 1) if week["views"] else 0,
        },
        "views_7d": series,
        "suggestions": suggestions[:3],
        "rooms": [room_out(db, r, stats) for r in rooms],
    }


@router.get("/rooms")
def rooms(user: User = Depends(landlord), db: Session = Depends(get_db)):
    stats = district_stats(db)
    rs = _rooms(db, user)
    counts = Counter(r.status for r in rs)
    return {"counts": {"all": len(rs), **counts}, "items": [room_out(db, r, stats) for r in rs]}


class RoomIn(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field("", max_length=5000)
    price: int = Field(ge=300_000, le=30_000_000)
    area: float | None = Field(None, ge=5, le=300)
    district: str
    street: str | None = None
    address: str = Field(min_length=3, max_length=255)
    room_type: str = "phong_tro"
    max_people: int | None = Field(None, ge=1, le=10)
    amenities: list[str] = []
    deposit_months: int | None = Field(None, ge=0, le=6)
    electricity_price: int | None = None
    water_price: int | None = None
    images: list[str] = []


@router.post("/rooms")
def create_room(body: RoomIn, user: User = Depends(landlord), db: Session = Depends(get_db)):
    if body.district not in DISTRICTS:
        raise HTTPException(422, "Khu vực không hợp lệ")
    lat, lng = approx_location(body.district, body.address)
    l = Listing(
        **body.model_dump(exclude={"amenities", "room_type"}),
        amenities=[a for a in body.amenities if a in AMENITY_KEYS],
        room_type=body.room_type if body.room_type in ROOM_TYPES else "phong_tro",
        lat=lat,
        lng=lng,
        owner_id=user.id,
        status="pending",
        poster_account_age_days=(utcnow() - user.created_at).days,
        ai_summary=extract(f"{body.title}. {body.description}").summary,
    )
    db.add(l)
    db.flush()
    l.quality_score = quality(l)
    apply_risk(db, l)
    notify_admins(db, "pending", f"Tin mới chờ duyệt: {l.title}", "/admin/kiem-duyet", "pending")
    db.commit()
    index_listing(l)
    return room_out(db, l, district_stats(db))


def _own_room(db: Session, user: User, room_id: int) -> Listing:
    l = db.get(Listing, room_id)
    if not l or (l.owner_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Không tìm thấy phòng")
    return l


@router.get("/rooms/{room_id}")
def room_detail(room_id: int, user: User = Depends(landlord), db: Session = Depends(get_db)):
    l = _own_room(db, user, room_id)
    fields = {k: getattr(l, k) for k in RoomIn.model_fields}
    return {**room_out(db, l, district_stats(db)), **fields}


class RoomPatch(BaseModel):
    price: int | None = Field(None, ge=300_000, le=30_000_000)
    status: Literal["active", "rented"] | None = None
    title: str | None = Field(None, min_length=5, max_length=200)
    description: str | None = Field(None, max_length=5000)
    area: float | None = Field(None, ge=5, le=300)
    district: str | None = None
    street: str | None = None
    address: str | None = Field(None, min_length=3, max_length=255)
    room_type: str | None = None
    max_people: int | None = Field(None, ge=1, le=10)
    amenities: list[str] | None = None
    deposit_months: int | None = Field(None, ge=0, le=6)
    electricity_price: int | None = None
    water_price: int | None = None
    images: list[str] | None = None
    refresh: bool = False


@router.patch("/rooms/{room_id}")
def update_room(room_id: int, body: RoomPatch, user: User = Depends(landlord), db: Session = Depends(get_db)):
    l = _own_room(db, user, room_id)
    if body.district is not None and body.district not in DISTRICTS:
        raise HTTPException(422, "Khu vực không hợp lệ")
    old_price, old_place = l.price, (l.district, l.address)
    data = body.model_dump(exclude_none=True, exclude={"refresh"})
    if "amenities" in data:
        data["amenities"] = [a for a in data["amenities"] if a in AMENITY_KEYS]
    if "room_type" in data and data["room_type"] not in ROOM_TYPES:
        data.pop("room_type")
    for k, v in data.items():
        setattr(l, k, v)
    if (l.district, l.address) != old_place:
        l.lat, l.lng = approx_location(l.district, l.address)
    if body.title or body.description:
        l.ai_summary = extract(f"{l.title}. {l.description}").summary
    if body.status == "active":
        l.available_from = None
    if body.refresh:
        l.posted_at = utcnow()
    if l.price < old_price and l.status == "active":
        notify_savers(db, l.id, "price_drop", f"{l.title} giảm giá còn {short_vnd(l.price)}", "price_drop")
    l.quality_score = quality(l)
    apply_risk(db, l)
    db.commit()
    index_listing(l)
    return room_out(db, l, district_stats(db))


@router.post("/upload")
async def upload(files: list[UploadFile] = File(...), user: User = Depends(landlord)):
    UPLOAD_DIR.mkdir(exist_ok=True)
    urls = []
    for f in files[:12]:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            raise HTTPException(422, "Chỉ nhận ảnh JPG, PNG hoặc WEBP")
        data = await f.read()
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(422, "Mỗi ảnh tối đa 5 MB")
        name = f"{uuid.uuid4().hex}{ext}"
        (UPLOAD_DIR / name).write_bytes(data)
        urls.append(f"/uploads/{name}")
    return {"urls": urls}


class AutofillIn(BaseModel):
    text: str = Field(min_length=10, max_length=4000)


@router.post("/autofill")
def autofill(body: AutofillIn, user: User = Depends(landlord), db: Session = Depends(get_db)):
    ex = extract(body.text)
    chips = []
    if ex.area:
        chips.append(f"{ex.area:g} m²")
    if ex.price:
        chips.append(short_vnd(ex.price))
    chips += [AMENITY_LABEL[a] for a in ex.amenities]
    if ex.street:
        chips.append(ex.street)
    est = estimate(db, ex.district, ex.area, ex.amenities, ex.room_type) if ex.district else None
    return {"fields": ex.model_dump(), "chips": chips, "estimate": est}


class PriceCheckIn(BaseModel):
    district: str
    area: float | None = None
    amenities: list[str] = []
    room_type: str = "phong_tro"
    price: int | None = None


@router.post("/price-check")
def price_check(body: PriceCheckIn, user: User = Depends(landlord), db: Session = Depends(get_db)):
    if body.district not in DISTRICTS:
        raise HTTPException(422, "Khu vực không hợp lệ")
    est = estimate(db, body.district, body.area, body.amenities, body.room_type)
    verdict = None
    if body.price:
        verdict = "ok" if est["low"] <= body.price <= est["high"] else "high" if body.price > est["high"] else "low"
    return {**est, "verdict": verdict}


@router.get("/stats")
def stats(days: int = 30, user: User = Depends(landlord), db: Session = Depends(get_db)):
    days = 7 if days <= 7 else 30
    rooms = _rooms(db, user)
    ids = [r.id for r in rooms]
    today = utcnow().date()
    cur = _sum_stats(db, ids, today - timedelta(days=days - 1), today + timedelta(days=1))
    prev = _sum_stats(db, ids, today - timedelta(days=2 * days - 1), today - timedelta(days=days - 1))
    daily = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        s = _sum_stats(db, ids, d, d + timedelta(days=1))
        daily.append({"label": d.strftime("%d/%m"), "views": s["views"], "contacts": s["contacts"]})
    # Từ khóa sinh viên hay tìm (từ nhật ký tìm kiếm), so với tiện ích phòng của chủ trọ.
    logs = db.query(SearchLog).filter(SearchLog.created_at >= utcnow() - timedelta(days=30)).all()
    counter: Counter = Counter()
    for lg in logs:
        f = lg.filters or {}
        for a in f.get("amenities", []):
            counter[AMENITY_LABEL.get(a, a).lower()] += 1
        if f.get("school_id"):
            counter["gần trường"] += 1
        if f.get("budget_max"):
            counter[f"dưới {short_vnd(f['budget_max'])}"] += 1
    total_logs = max(1, len(logs))
    per_room = []
    for r in rooms:
        if r.status in ("active", "rented") and r.views:
            per_room.append({"id": r.id, "name": r.title, "views": r.views, "contacts": r.contacts, "rate": round(r.contacts / r.views * 100, 1)})
    per_room.sort(key=lambda x: -x["views"])
    return {
        "days": days,
        "kpis": {
            **cur,
            "impressions_change": _pct(cur["impressions"], prev["impressions"]),
            "ctr": round(cur["views"] / cur["impressions"] * 100, 1) if cur["impressions"] else 0,
            "contact_rate": round(cur["contacts"] / cur["views"] * 100, 1) if cur["views"] else 0,
            "saves_change": cur["saves"] - prev["saves"],
        },
        "daily": daily,
        "funnel": [
            {"label": "Hiển thị trong kết quả", "value": cur["impressions"]},
            {"label": "Xem chi tiết", "value": cur["views"]},
            {"label": "Xem bài gốc, liên hệ", "value": cur["contacts"]},
        ],
        "keywords": [{"keyword": k, "share": round(v / total_logs, 2)} for k, v in counter.most_common(5)],
        "per_room": per_room[:6],
    }


class LandlordProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = None
    bio: str | None = Field(None, max_length=500)


@router.get("/profile")
def profile(user: User = Depends(landlord), db: Session = Depends(get_db)):
    rooms = _rooms(db, user)
    ids = [r.id for r in rooms]
    reported = db.query(func.count(func.distinct(Report.listing_id))).filter(Report.listing_id.in_(ids)).scalar() if ids else 0
    steps = [
        {"label": "Số điện thoại", "done": user.phone_verified, "text": "Đã xác minh" if user.phone_verified else "Chưa xác minh"},
        {"label": "Địa chỉ khu trọ", "done": user.address_verified, "text": "Đã xác minh qua ảnh và vị trí" if user.address_verified else "Chưa xác minh"},
        {"label": "Giấy tờ chủ sở hữu", "done": user.id_verification == "verified",
         "text": {"none": "Chưa gửi", "pending": "Đang chờ duyệt, 1 – 2 ngày", "verified": "Đã xác minh"}[user.id_verification]},
    ]
    return {
        "user": user_out(user),
        "room_count": len(rooms),
        "address": next((r.address for r in rooms), ""),
        "verification": steps,
        "trust": {"report_rate": round(reported / len(rooms) * 100) if rooms else 0, "first_approval": 92, "response_hours": 2},
    }


@router.put("/profile")
def update_profile(body: LandlordProfileIn, user: User = Depends(landlord), db: Session = Depends(get_db)):
    user.full_name, user.phone, user.bio = body.full_name, body.phone, body.bio
    db.commit()
    return user_out(user)
