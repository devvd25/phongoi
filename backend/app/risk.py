"""Chấm điểm rủi ro lừa đảo đa tín hiệu (ML + Rule) và đánh giá chất lượng tin đăng."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from .catalog import SCAM_KEYWORDS, norm
from .extract import is_all_inclusive_utilities, strip_crawled_noise
from .ml_classifier import classify_post
from .models import Listing, Report, User
from .money import short_vnd
from .pricing import segmented_district_stats


def level_of(score: int) -> str:
    return "high" if score >= 65 else "medium" if score >= 35 else "low"


def assess(db: Session, listing: Listing) -> dict:
    seg = segmented_district_stats(db, listing.district or "Hải Châu", listing.room_type or "phong_tro", price=listing.price)
    score, reasons, checks = 0, [], []

    if seg and seg["median"] and listing.price:
        ratio = listing.price / seg["median"]
        if ratio < 0.48:
            score += 45
            reasons.append(f"Giá thấp hơn {round((1 - ratio) * 100)}% so với trung vị phân khúc {listing.district} ({short_vnd(seg['median'])})")
        elif ratio < 0.62:
            score += 25
            reasons.append(f"Giá thấp bất thường, kém {round((1 - ratio) * 100)}% so với trung vị {listing.district}")
        else:
            checks.append(f"Giá thuê phù hợp mặt bằng {seg['segment_label'].lower()}")

    raw_text = f"{listing.title or ''}. {listing.description or ''}"
    text = norm(raw_text)
    hits = [k for k in SCAM_KEYWORDS if norm(k) in text]
    if hits:
        score += 32
        reasons.append("Yêu cầu chuyển cọc trước khi xem phòng trực tiếp")

    # Tín hiệu ML phân loại người đăng (Chính chủ vs Môi giới/Hệ thống)
    cls = classify_post(raw_text)
    if cls.get("is_broker"):
        score += 6
        checks.append("Nguồn hệ thống/môi giới — xác nhận xem phòng miễn phí trước khi đi")
    else:
        checks.append("Ngôn ngữ tin đăng tự nhiên (Chính chủ / Người thuê nhượng lại)")

    # Tín hiệu minh bạch chi phí điện/nước
    all_inclusive = is_all_inclusive_utilities(raw_text)
    if all_inclusive:
        checks.append("Đã bao gồm chi phí điện/nước trong tiền phòng")
    elif listing.electricity_price and listing.water_price:
        checks.append("Công khai rõ đơn giá điện và nước sinh hoạt")
    else:
        score += 5

    dup_images = 0
    if listing.image_fingerprint and listing.id:
        dup_images = (
            db.query(func.count(Listing.id))
            .filter(Listing.image_fingerprint == listing.image_fingerprint, Listing.id != listing.id, Listing.address != listing.address)
            .scalar()
            or 0
        )
    if not (listing.images or []):
        score += 8
        reasons.append("Tin đăng chưa có ảnh chụp thực tế")
    elif dup_images:
        score += 20
        reasons.append(f"Bộ ảnh trùng với {dup_images} tin ở địa chỉ khác")
    else:
        checks.append(f"Có {len(listing.images or [])} ảnh phòng thực tế, không trùng lặp bất thường")

    owner = db.get(User, listing.owner_id) if listing.owner_id else None
    if owner and (owner.phone_verified or owner.id_verification == "verified"):
        checks.append("Chủ trọ đã xác minh danh tính trên Phòng Ơi")
    elif listing.poster_account_age_days is not None:
        if listing.poster_account_age_days < 7:
            score += 10
            reasons.append(f"Tài khoản đăng tin mới tạo {listing.poster_account_age_days} ngày")
        elif listing.poster_account_age_days > 365:
            checks.append(f"Người đăng hoạt động hơn {listing.poster_account_age_days // 365} năm")

    if not listing.area or not listing.address:
        score += 5
        reasons.append("Thiếu diện tích hoặc địa chỉ chi tiết")
    elif not listing.street:
        score += 3

    open_reports = 0
    if listing.id:
        open_reports = (
            db.query(func.count(Report.id))
            .filter(Report.listing_id == listing.id, Report.status.in_(["new", "processing", "resolved"]))
            .scalar()
            or 0
        )
    if open_reports:
        score += min(24, 8 * open_reports)
        reasons.append(f"{open_reports} sinh viên đã báo cáo tin này")
    else:
        checks.append("Chưa có báo cáo vi phạm từ sinh viên")

    score = min(100, score)
    if listing.risk_dismissed:
        score = min(score, 20)
    return {"score": score, "level": level_of(score), "reasons": reasons, "checks": checks}


def apply(db: Session, listing: Listing) -> None:
    r = assess(db, listing)
    listing.risk_score, listing.risk_level, listing.risk_reasons = r["score"], r["level"], r["reasons"]


def quality(listing: Listing) -> float:
    """Chấm điểm chất lượng thông tin tin đăng trên thang 3.5 – 9.8."""
    s = 1.5
    imgs = len(listing.images or [])
    if imgs >= 6:
        s += 2.6
    elif imgs >= 4:
        s += 2.2
    elif imgs >= 2:
        s += 1.7
    elif imgs == 1:
        s += 1.0

    clean_desc = strip_crawled_noise(listing.description or "")
    words = len(clean_desc.split())
    s += 1.4 * min(words, 90) / 90
    s += 1.1 * min(len(listing.amenities or []), 6) / 6

    if listing.price:
        s += 0.5
    if listing.area:
        s += 0.7
    if listing.street:
        s += 0.7
    elif listing.address and listing.address != f"{listing.district}, Đà Nẵng":
        s += 0.4
    if listing.lat and listing.lng:
        s += 0.4

    raw_text = f"{listing.title or ''} {listing.description or ''}"
    all_inc = is_all_inclusive_utilities(raw_text)
    if all_inc or (listing.electricity_price and listing.water_price):
        s += 0.6
    elif listing.electricity_price or listing.water_price:
        s += 0.3
    if listing.deposit_months is not None or listing.max_people is not None:
        s += 0.3

    return round(max(3.5, min(9.8, s)), 1)
