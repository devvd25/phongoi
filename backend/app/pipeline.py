"""Luồng xử lý một tin thô: làm sạch -> trích xuất -> gộp trùng -> chấm rủi ro -> lưu -> đánh chỉ mục."""

import hashlib
from datetime import datetime, timedelta

from pydantic import BaseModel
from sqlalchemy.orm import Session

from .catalog import find_districts, norm
from .db import utcnow
from .extract import extract
from .geo import approx_location
from .ml_classifier import classify_post
from .models import ExtractionIssue, Listing, ListingSource
from .risk import apply as apply_risk
from .risk import quality
from .search import index_listing
from .serializers import clean_listing_images


class RawPost(BaseModel):
    source_name: str
    url: str
    text: str
    images: list[str] = []
    posted_at: datetime | None = None
    poster_account_age_days: int | None = None


RELEVANT = ("phong", "tro", "thue", "can ho", "o ghep", "studio")
OUTSIDE_DANANG = (
    "ha noi",
    "ho chi minh",
    "sai gon",
    "quang nam",
    "hoi an",
    "thua thien hue",
    "thanh pho hue",
    "nha trang",
    "can tho",
    "hai phong",
)


def is_relevant(text: str) -> bool:
    n = norm(text)
    return len(n) >= 40 and any(k in n for k in RELEVANT)


def is_expired_or_stale_post(text: str) -> tuple[bool, str]:
    """Phát hiện và loại bỏ các tin đăng đã hết hạn hiển thị hoặc tin cũ nhiều năm trước."""
    import re
    from .extract import strip_crawled_noise

    cleaned = strip_crawled_noise(text or "")
    n = norm(cleaned)

    if re.search(r"\b(?:tin\s+dang\s+nay\s+da\s+het\s+han|tin\s+dang\s+da\s+qua\s+han|tin\s+da\s+het\s+han|da\s+cho\s+thue\s+xong)\b", n):
        return True, "Tin đăng đã hết hạn trên trang gốc"

    if m := re.search(r"\b(?:cap\s+nhat|dang)\s*:?\s*(\d+)\s*nam\s+truoc\b", n):
        return True, f"Tin đăng đã cũ ({m.group(1)} năm trước)"

    if m := re.search(r"\b\d{1,2}/\d{1,2}/(201\d|202[0-5])\b", n):
        return True, f"Tin đăng cũ từ năm {m.group(1)}"

    return False, ""


def is_danang_post(raw: RawPost) -> bool:
    text = norm(raw.text)
    explicitly_local = "da nang" in text or bool(find_districts(raw.text))
    if not explicitly_local and any(place in text for place in OUTSIDE_DANANG):
        return False
    return explicitly_local or "da nang" in norm(raw.source_name)


def _tokens(text: str) -> set[str]:
    from .extract import strip_crawled_noise

    cleaned = strip_crawled_noise(text or "")
    stop = {"cho", "thue", "phong", "tro", "can", "nang", "quan", "phuong", "duong", "thang", "dong", "gia", "apartment", "tai"}
    return {w for w in norm(cleaned[:450]).split() if len(w) > 2 and w not in stop}


def find_duplicate(db: Session, district: str | None, price: int, text: str, street: str | None = None, area: float | None = None) -> Listing | None:
    """Tin trùng: cùng khu vực, giá lệch ≤ 5%, cùng đường/diện tích VÀ nội dung mô tả chính giống ≥ 75%."""
    if not district:
        return None
    cands = (
        db.query(Listing)
        .filter(
            Listing.district == district,
            Listing.price.between(int(price * 0.95), int(price * 1.05)),
            Listing.posted_at >= utcnow() - timedelta(days=60),
            Listing.status != "hidden",
        )
        .all()
    )
    tk = _tokens(text)
    for c in cands:
        if street and c.street and c.street != street:
            continue
        if area and c.area and abs(c.area - area) > 2:
            continue
        other = _tokens(f"{c.title or ''}. {c.description or ''}")
        if tk and other and len(tk & other) / len(tk | other) >= 0.75:
            return c
    return None


def process_raw(db: Session, raw: RawPost) -> dict:
    raw.images = clean_listing_images(raw.images)
    if not is_relevant(raw.text):
        return {"status": "rejected", "stage": "clean"}
    expired, exp_reason = is_expired_or_stale_post(raw.text)
    if expired:
        return {"status": "rejected", "stage": "clean", "reason": exp_reason}
    cls = classify_post(raw.text)
    if not cls["is_rental"]:
        reason_label = "Tin tìm phòng" if cls["intent"] == "room_seeker" else "Tin spam / dịch vụ"
        return {"status": "rejected", "stage": "clean", "reason": f"Loại bởi ML CPU: {reason_label} ({cls['intent']})"}
    if not is_danang_post(raw):
        return {"status": "rejected", "stage": "scope", "reason": "Ngoài phạm vi Đà Nẵng"}
    ex = extract(raw.text)
    summary_items = list(ex.summary) if isinstance(ex.summary, list) else ([str(ex.summary)] if ex.summary else [])
    if cls["is_broker"] and not any("Môi giới" in s for s in summary_items):
        summary_items.append("Nguồn đăng: Môi giới / Hệ thống")
    ex.summary = summary_items
    if ex.price is None:
        db.add(ExtractionIssue(snippet=raw.text[:300], reason="Thiếu giá", payload=ex.model_dump()))
        db.commit()
        return {"status": "rejected", "stage": "extract", "reason": "Thiếu giá"}

    dup = find_duplicate(db, ex.district, ex.price, raw.text, ex.street, ex.area)
    if dup:
        norm_new_url = (raw.url or "").split("?")[0].rstrip("/").lower()
        existing_urls = {(s.url or "").split("?")[0].rstrip("/").lower() for s in dup.sources if s.url}
        if not norm_new_url or norm_new_url not in existing_urls:
            dup.sources.append(ListingSource(source_name=raw.source_name, url=raw.url, raw_text=raw.text, posted_at=raw.posted_at or utcnow()))
        dup.source_count = len(dup.sources)
        if raw.images and not dup.images:
            dup.images = raw.images
            dup.image_fingerprint = hashlib.md5(raw.images[0].encode()).hexdigest()
            dup.quality_score = quality(dup)
        if ex.area and not dup.area:
            dup.area = ex.area
            dup.quality_score = quality(dup)
        db.commit()
        index_listing(dup)
        return {"status": "duplicate", "listing_id": dup.id}

    address = ", ".join(x for x in (ex.address, ex.district, "Đà Nẵng") if x)
    lat, lng = approx_location(ex.district, address)
    listing = Listing(
        title=ex.title,
        description=raw.text,
        price=ex.price,
        area=ex.area,
        district=ex.district or "Hải Châu",
        street=ex.street,
        address=address,
        lat=lat,
        lng=lng,
        room_type=ex.room_type,
        max_people=ex.max_people,
        amenities=ex.amenities,
        deposit_months=ex.deposit_months,
        electricity_price=ex.electricity_price,
        water_price=ex.water_price,
        images=raw.images,
        image_fingerprint=hashlib.md5(raw.images[0].encode()).hexdigest() if raw.images else None,
        poster_account_age_days=raw.poster_account_age_days,
        ai_summary=ex.summary,
        posted_at=raw.posted_at or utcnow(),
        sources=[ListingSource(source_name=raw.source_name, url=raw.url, raw_text=raw.text, posted_at=raw.posted_at or utcnow())],
    )
    db.add(listing)
    db.flush()
    listing.quality_score = quality(listing)
    apply_risk(db, listing)
    db.commit()
    index_listing(listing)
    return {"status": "new", "listing_id": listing.id, "risk_level": listing.risk_level, "engine": ex.engine}
