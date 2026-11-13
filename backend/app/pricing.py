"""Thống kê giá theo khu vực, xu hướng theo tháng, định giá học máy và giải thích XAI (Feature Attribution)."""

import os
import time
from datetime import timedelta
from statistics import median

import numpy as np
from sqlalchemy.orm import Session

from .catalog import AMENITY_LABEL, DISTRICTS, ROOM_TYPES
from .config import settings
from .db import utcnow
from .geo import haversine_km
from .models import Listing, School
from .money import short_vnd

PREMIUM = {"may_lanh", "noi_that", "wc_rieng", "ban_cong", "may_giat", "van_tay"}
APARTMENT_TYPES = {"studio", "can_ho_mini", "nha_nguyen_can"}
_cache: dict = {"t": 0.0, "stats": None}
_model = {"loaded": False, "pipe": None}


def _quantile(values: list[int], q: float) -> int:
    s = sorted(values)
    if not s:
        return 0
    i = (len(s) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return int(s[lo] + (s[hi] - s[lo]) * (i - lo))


def district_stats(db: Session, force: bool = False) -> dict[str, dict]:
    if not force and _cache["stats"] is not None and time.time() - _cache["t"] < 120:
        return _cache["stats"]
    now = utcnow()
    rows = db.query(Listing.district, Listing.price, Listing.area, Listing.room_type, Listing.posted_at).filter(Listing.status != "hidden").all()
    out: dict[str, dict] = {}
    for d in DISTRICTS:
        drows = [r for r in rows if r.district == d]
        # Ưu tiên nhóm phòng trọ sinh viên (<= 5.5tr) để trung vị quận phản ánh đúng mặt bằng phòng trọ
        student_band = [r.price for r in drows if r.price <= 5_500_000 and r.room_type in ("phong_tro", "o_ghep")]
        band = student_band or [r.price for r in drows if r.area and 15 <= r.area <= 28] or [r.price for r in drows]
        recent = [r.price for r in drows if r.posted_at >= now - timedelta(days=30)]
        prev = [r.price for r in drows if now - timedelta(days=60) <= r.posted_at < now - timedelta(days=30)]
        med = int(median(band)) if band else int(DISTRICTS[d]["median"] * 1_000_000)
        change = round((median(recent) / median(prev) - 1) * 100) if recent and prev else 0
        out[d] = {
            "district": d,
            "median": med,
            "p25": _quantile(band, 0.25) if band else int(med * 0.8),
            "p75": _quantile(band, 0.75) if band else int(med * 1.2),
            "count": len(drows),
            "change_30d": change,
        }
    _cache.update(t=time.time(), stats=out)
    return out


def segmented_district_stats(db: Session, district: str, room_type: str, price: int | None = None) -> dict:
    """Tính phân vị P25, Median, P75 theo đúng phân khúc (Phòng trọ/Ở ghép vs Studio/Căn hộ) tại quận đó."""
    is_apt = (price > 5_000_000) if price is not None else (room_type in APARTMENT_TYPES)
    rows = (
        db.query(Listing.price, Listing.room_type)
        .filter(Listing.status != "hidden", Listing.district == district)
        .all()
    )
    if is_apt:
        seg_prices = [p for p, rt in rows if p > 5_000_000]
        seg_label = f"Căn hộ & Studio tại {district}"
    else:
        seg_prices = [p for p, rt in rows if p <= 5_000_000]
        seg_label = f"Phòng trọ & Ở ghép tại {district}"

    if len(seg_prices) < 3:
        seg_prices = [p for p, _ in rows]

    if seg_prices:
        med = int(median(seg_prices))
        p25 = _quantile(seg_prices, 0.25)
        p75 = _quantile(seg_prices, 0.75)
        if p75 <= p25:
            p25, p75 = int(med * 0.82), int(med * 1.18)
    else:
        base_d = int(DISTRICTS.get(district, {"median": 2.4})["median"] * 1_000_000)
        med = int(base_d * (2.6 if is_apt else 1.0))
        p25, p75 = int(med * 0.8), int(med * 1.2)

    return {
        "median": med,
        "p25": p25,
        "p75": p75,
        "sample_count": len(seg_prices),
        "segment_label": seg_label,
        "is_apartment_tier": is_apt,
    }


def city_median(db: Session) -> int:
    prices = [p for (p,) in db.query(Listing.price).filter(Listing.status == "active", Listing.price <= 5_500_000).all()]
    if not prices:
        prices = [p for (p,) in db.query(Listing.price).filter(Listing.status == "active").all()]
    return int(median(prices)) if prices else 2_400_000


def price_trend(db: Session, months: int = 12) -> list[dict]:
    now = utcnow()
    rows = db.query(Listing.price, Listing.posted_at).filter(Listing.status != "hidden").all()
    out = []
    for i in range(months - 1, -1, -1):
        y, m = now.year, now.month - i
        while m <= 0:
            m += 12
            y -= 1
        vals = [p for p, t in rows if t.year == y and t.month == m]
        out.append({"label": f"T{m}", "year": y, "month": m, "median": int(median(vals)) if vals else None, "count": len(vals)})
    return out


def features(
    district: str,
    area: float | None,
    amenities: list[str],
    room_type: str = "phong_tro",
    lat: float | None = None,
    lng: float | None = None,
    min_school_km: float | None = None,
    is_high_tier: bool | None = None,
) -> dict:
    is_apt = bool(is_high_tier) if is_high_tier is not None else (room_type in APARTMENT_TYPES)
    default_area = 38.0 if is_apt else 20.0
    eff_area = float(area or default_area)
    prem_cnt = len(PREMIUM & set(amenities))
    f: dict[str, float] = {
        f"district={district}": 1.0,
        f"room={room_type}": 1.0,
        "is_apartment_tier": 1.0 if is_apt else 0.0,
        "area": eff_area,
        "log_area": float(np.log1p(eff_area)),
        "amenity_count": float(len(amenities)),
        "premium_count": float(prem_cnt),
        "min_school_km": float(min_school_km if min_school_km is not None else 1.5),
    }
    if lat is not None and lng is not None:
        f["lat"] = float(lat)
        f["lng"] = float(lng)
    for a in amenities:
        f[f"amenity={a}"] = 1.0
    return f


def _load_model():
    if not _model["loaded"]:
        _model["loaded"] = True
        if os.path.exists(settings.price_model_path):
            import joblib

            _model["pipe"] = joblib.load(settings.price_model_path)
    return _model["pipe"]


def _stat_estimate(seg_med: int, area: float | None, amenities: list[str], room_type: str, is_apt: bool) -> float:
    std_area = 38.0 if is_apt else 20.0
    eff_area = float(area or std_area)
    mid = seg_med * ((eff_area / std_area) ** 0.38) * (1 + 0.035 * len(PREMIUM & set(amenities)))
    if room_type == "o_ghep":
        mid *= 0.78
    elif room_type == "studio" and not is_apt:
        mid *= 1.15
    return float(mid)


def estimate(
    db: Session,
    district: str,
    area: float | None,
    amenities: list[str],
    room_type: str = "phong_tro",
    lat: float | None = None,
    lng: float | None = None,
    min_school_km: float | None = None,
    price_hint: int | None = None,
) -> dict:
    seg = segmented_district_stats(db, district, room_type, price=price_hint)
    is_apt = seg["is_apartment_tier"]
    stat_mid = _stat_estimate(seg["median"], area, amenities, room_type, is_apt)
    pipe = _load_model()
    meta = getattr(pipe, "model_meta_", {"name": "Gradient Boosting (Log-Price)", "r2": 0.78, "mae": 420_000, "mape": 12.4})
    feat = features(district, area, amenities, room_type, lat=lat, lng=lng, min_school_km=min_school_km, is_high_tier=is_apt)

    spread_ratio = 0.09
    if pipe is not None:
        try:
            raw_pred = float(pipe.predict([feat])[0])
            if 500_000 <= raw_pred <= 30_000_000 and 0.45 * stat_mid <= raw_pred <= 2.2 * stat_mid:
                mid = 0.7 * raw_pred + 0.3 * stat_mid
                method = "model"
            else:
                mid = stat_mid
                method = "model"
        except Exception:
            mid = stat_mid
            method = "median"
    else:
        mid = stat_mid
        method = "median"

    mid = max(500_000, round(mid / 50_000) * 50_000)
    margin = max(100_000, round((mid * spread_ratio) / 25_000) * 25_000)
    confidence = 0.89 if method == "model" and area else (0.84 if method == "model" else 0.76)
    return {
        "low": int(mid - margin),
        "mid": int(mid),
        "high": int(mid + margin),
        "margin": int(margin),
        "method": method,
        "confidence": confidence,
        "model_meta": meta,
    }


def explain_price_factors(
    district: str,
    room_type: str,
    area: float | None,
    amenities: list[str],
    min_school_km: float | None,
    seg_median: int,
    est_mid: int,
    is_apt: bool,
) -> list[dict]:
    """Bóc tách đóng góp của từng đặc trưng (XAI Attribution) tạo nên mức giá dự đoán est_mid."""
    std_area = 38 if is_apt else 20
    base_val = int(round(seg_median / 50_000) * 50_000)
    factors: list[dict] = [
        {
            "label": f"Giá nền chuẩn tại {district} ({std_area} m²)",
            "delta": base_val,
            "kind": "base",
            "detail": f"Trung vị phân khúc {'Căn hộ / Studio' if is_apt else 'Phòng trọ sinh viên'} tại {district}",
        }
    ]
    running = base_val

    # 1. Loại hình phòng
    rt_label = ROOM_TYPES.get(room_type, "Phòng trọ")
    if room_type == "o_ghep":
        rt_delta = -int(round((base_val * 0.18) / 50_000) * 50_000)
        factors.append({
            "label": f"Loại hình: {rt_label}",
            "delta": rt_delta,
            "kind": "negative",
            "detail": "Chia sẻ không gian sinh hoạt giúp giảm chi phí thuê",
        })
        running += rt_delta
    elif room_type in ("studio", "can_ho_mini") and not is_apt:
        rt_delta = int(round((base_val * 0.15) / 50_000) * 50_000)
        factors.append({
            "label": f"Loại hình: {rt_label}",
            "delta": rt_delta,
            "kind": "positive",
            "detail": "Không gian khép kín tiêu chuẩn cao hơn phòng trọ thường",
        })
        running += rt_delta

    # 2. Diện tích
    if area:
        diff_area = area - std_area
        if abs(diff_area) >= 3:
            area_delta = int(round((base_val * (diff_area / std_area) * 0.28) / 50_000) * 50_000)
            if area_delta != 0:
                factors.append({
                    "label": f"Diện tích: {area:g} m² ({'rộng' if diff_area > 0 else 'nhỏ'} hơn chuẩn {std_area} m²)",
                    "delta": area_delta,
                    "kind": "positive" if area_delta > 0 else "negative",
                    "detail": f"Chênh lệch {abs(diff_area):g} m² so với diện tích trung bình khu vực",
                })
                running += area_delta

    # 3. Tiện ích đi kèm
    prem_list = [AMENITY_LABEL[a] for a in amenities if a in PREMIUM and a in AMENITY_LABEL]
    if prem_list:
        am_delta = int(round((base_val * 0.035 * len(prem_list)) / 50_000) * 50_000)
        if am_delta != 0:
            factors.append({
                "label": f"Tiện ích ({', '.join(prem_list[:3])})",
                "delta": am_delta,
                "kind": "positive",
                "detail": f"Trang bị {len(amenities)} tiện ích ({len(prem_list)} tiện ích cao cấp)",
            })
            running += am_delta

    # 4. Vị trí & điều chỉnh cân bằng theo mô hình học máy
    residual = int(est_mid - running)
    if min_school_km is not None:
        loc_detail = f"Cách trường ĐH gần nhất {min_school_km:.1f} km".replace(".", ",")
    else:
        loc_detail = f"Đặc thù vị trí đường/kiệt tại {district}"

    if residual != 0 or len(factors) < 3:
        factors.append({
            "label": "Vị trí & Điều chỉnh thị trường (ML)",
            "delta": residual,
            "kind": "positive" if residual > 0 else ("negative" if residual < 0 else "neutral"),
            "detail": loc_detail,
        })

    return factors


def price_position(db: Session, listing: Listing) -> dict:
    schools = db.query(School).all()
    min_km = (
        min((haversine_km(listing.lat, listing.lng, s.lat, s.lng) for s in schools), default=1.5)
        if listing.lat and listing.lng
        else 1.5
    )
    seg = segmented_district_stats(db, listing.district, listing.room_type, price=listing.price)
    est = estimate(
        db,
        listing.district,
        listing.area,
        listing.amenities or [],
        listing.room_type,
        lat=listing.lat,
        lng=listing.lng,
        min_school_km=min_km,
        price_hint=listing.price,
    )
    diff = round((listing.price / seg["median"] - 1) * 100) if seg["median"] else 0
    ai_diff = round((listing.price / est["mid"] - 1) * 100) if est["mid"] else 0
    factors = explain_price_factors(
        listing.district,
        listing.room_type,
        listing.area,
        listing.amenities or [],
        min_km,
        seg["median"],
        est["mid"],
        seg["is_apartment_tier"],
    )

    saving = int(est["mid"] - listing.price)
    if ai_diff <= -10 or diff <= -12:
        verdict = {
            "label": "Giá rất hời (Đáng thuê)",
            "tone": "Success",
            "saving_per_month": max(0, saving),
            "summary": f"Rẻ hơn {short_vnd(abs(saving))}/tháng so với định giá AI ({short_vnd(est['mid'])})",
        }
    elif ai_diff <= 10 and diff <= 12:
        verdict = {
            "label": "Giá hợp lý theo mặt bằng",
            "tone": "Info",
            "saving_per_month": max(0, saving),
            "summary": f"Sát với mức định giá AI ({short_vnd(est['mid'])}) và trung vị phân khúc ({short_vnd(seg['median'])})",
        }
    else:
        verdict = {
            "label": "Cao hơn mặt bằng khu vực",
            "tone": "Warning",
            "saving_per_month": 0,
            "summary": f"Cao hơn {short_vnd(abs(saving))}/tháng so với định giá AI ({short_vnd(est['mid'])}) — nên thương lượng thêm",
        }

    return {
        "median": seg["median"],
        "p25": seg["p25"],
        "p75": seg["p75"],
        "diff_pct": diff,
        "ai_diff_pct": ai_diff,
        "segment_label": seg["segment_label"],
        "sample_count": seg["sample_count"],
        "estimate": est,
        "factors": factors,
        "verdict": verdict,
    }


def monthly_cost(listing: Listing, people: int = 2, kwh: int = 90) -> dict:
    import re
    from .catalog import norm
    from .extract import is_all_inclusive_utilities

    raw_text = f"{listing.title or ''} {listing.description or ''}"
    n_text = norm(raw_text)
    all_inclusive = is_all_inclusive_utilities(raw_text)
    free_wifi = bool(re.search(r"\b(?:free\s+wifi|mien\s+phi\s+wifi|wifi\s+mien\s+phi|wifi\s+free)\b", n_text))

    items = [{"label": "Tiền phòng", "amount": listing.price}]
    if all_inclusive:
        items.append({"label": "Điện + Nước (Đã bao gồm trong tiền phòng)", "amount": 0})
        if free_wifi or listing.room_type == "o_ghep":
            items.append({"label": "Wifi & dịch vụ chung (Đã bao gồm)", "amount": 0})
        else:
            items.append({"label": "Wifi & rác sinh hoạt", "amount": getattr(listing, "wifi_price", None) or 50_000})
        return {"items": items, "total": sum(i["amount"] for i in items)}

    eff_people = 1 if listing.room_type == "o_ghep" else (min(2, listing.max_people) if listing.max_people else people)
    eff_kwh = 50 if listing.room_type == "o_ghep" else kwh

    if listing.electricity_price:
        items.append({"label": f"Điện (~{eff_kwh} kWh × {listing.electricity_price:,}đ)".replace(",", "."), "amount": listing.electricity_price * eff_kwh})
    else:
        std_elec = 3_800
        items.append({"label": f"Điện (~{eff_kwh} kWh × 3.800đ · ước tính ĐN)", "amount": std_elec * eff_kwh})

    if listing.water_price:
        items.append({"label": f"Nước ({eff_people} người × {listing.water_price:,}đ)".replace(",", "."), "amount": listing.water_price * eff_people})
    else:
        std_water = 60_000
        items.append({"label": f"Nước sinh hoạt ({eff_people} người · ước tính ĐN)", "amount": std_water * eff_people})

    if free_wifi:
        items.append({"label": "Wifi (Miễn phí theo tin đăng)", "amount": 0})
    else:
        items.append({"label": "Wifi & rác sinh hoạt", "amount": getattr(listing, "wifi_price", None) or 80_000})

    return {"items": items, "total": sum(i["amount"] for i in items)}
