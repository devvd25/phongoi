"""Script chuẩn hóa toàn bộ dữ liệu tin đăng hiện có trong phongoi.db theo 6 Module Backend mới."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal
from app.extract import extract_rule, strip_crawled_noise
from app.geo import approx_location
from app.ml_classifier import classify_post
from app.models import Listing, ListingStat, Report, SavedListing
from app.pipeline import is_expired_or_stale_post
from app.pricing import _cache
from app.risk import apply as apply_risk
from app.risk import quality
from app.routes_public import deduplicate_sources


def run_normalization() -> dict:
    db = SessionLocal()
    try:
        listings = db.query(Listing).all()
        updated_locations = 0
        deduped_sources = 0
        removed_expired = 0
        active_listings: list[Listing] = []

        for l in listings:
            src_texts = " ".join((s.raw_text or "") for s in l.sources)
            full_check_text = f"{l.title or ''}. {l.description or ''} {src_texts}"
            is_exp, _ = is_expired_or_stale_post(full_check_text)
            if is_exp or "russian tourists return" in (l.title or "").lower():
                db.query(ListingStat).filter_by(listing_id=l.id).delete()
                db.query(SavedListing).filter_by(listing_id=l.id).delete()
                db.query(Report).filter_by(listing_id=l.id).delete()
                for s in list(l.sources):
                    db.delete(s)
                db.delete(l)
                removed_expired += 1
                continue
            active_listings.append(l)

        listings = active_listings
        for l in listings:
            raw_combined = f"{l.title or ''}. {l.description or ''}"
            ex = extract_rule(raw_combined)

            old_addr = l.address
            old_dist = l.district
            if ex.district:
                l.district = ex.district
            # Chỉ giữ street mới đã kiểm chứng từ nội dung chính (xóa street bị gán nhầm từ footer cũ)
            l.street = ex.street
            new_addr = ", ".join(x for x in (ex.address, l.district, "Đà Nẵng") if x)
            l.address = new_addr
            l.lat, l.lng = approx_location(l.district, l.address)
            if l.address != old_addr or l.district != old_dist:
                updated_locations += 1

            if ex.amenities:
                l.amenities = ex.amenities
            if ex.room_type:
                l.room_type = ex.room_type
            if ex.max_people and not l.max_people:
                l.max_people = ex.max_people
            if ex.deposit_months is not None and l.deposit_months is None:
                l.deposit_months = ex.deposit_months
            if ex.electricity_price and not l.electricity_price:
                l.electricity_price = ex.electricity_price
            if ex.water_price and not l.water_price:
                l.water_price = ex.water_price

            # Làm sạch mô tả (cắt bỏ menu điều hướng và footer quảng cáo)
            cleaned_desc = strip_crawled_noise(l.description or "")
            if len(cleaned_desc) >= 25:
                l.description = cleaned_desc

            # Khử trùng các bản ghi ListingSource trùng URL
            unique_srcs = deduplicate_sources(list(l.sources))
            if len(unique_srcs) < len(l.sources):
                keep_ids = {s.id for s in unique_srcs}
                for s in list(l.sources):
                    if s.id not in keep_ids:
                        db.delete(s)
                        deduped_sources += 1
            l.source_count = max(1, len(unique_srcs))

            # Cập nhật tóm tắt AI cơ sở
            cls = classify_post(f"{l.title or ''}. {l.description or ''}")
            summary_items = list(ex.summary)
            if cls.get("is_broker") and not any("Môi giới" in s for s in summary_items):
                summary_items.append("Nguồn đăng: Môi giới / Hệ thống")
            l.ai_summary = summary_items

        db.flush()
        # Reset cache thống kê quận để tính lại trung vị sau khi chuẩn hóa đúng Quận
        _cache.update(t=0.0, stats=None)

        for l in listings:
            l.quality_score = quality(l)
            apply_risk(db, l)

        db.commit()
        return {
            "total_listings": len(listings),
            "removed_expired": removed_expired,
            "updated_locations": updated_locations,
            "deduped_sources": deduped_sources,
        }
    finally:
        db.close()


if __name__ == "__main__":
    res = run_normalization()
    print("Normalized DB:", res)
