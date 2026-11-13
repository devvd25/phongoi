"""Tính mức phù hợp giữa tin đăng và nhu cầu sinh viên, kèm lý do gợi ý sát thực tế."""

from .catalog import AMENITY_LABEL, ROOM_TYPES
from .extract import is_all_inclusive_utilities
from .geo import haversine_km
from .models import Listing, School
from .money import short_vnd
from .query_parser import SearchFilters

WEIGHTS = {"budget": 0.35, "distance": 0.30, "amenities": 0.20, "safety": 0.15}


def match(listing: Listing, f: SearchFilters, school: School | None, stats: dict) -> dict:
    reasons: list[str] = []
    if f.budget_max:
        budget = 1.0 if listing.price <= f.budget_max else max(0.0, 1 - (listing.price - f.budget_max) / f.budget_max * 3)
        if listing.price <= f.budget_max:
            reasons.append(f"Trong ngân sách {short_vnd(f.budget_max)}")
    else:
        budget = 0.88

    distance_km = None
    if school and listing.lat and listing.lng:
        distance_km = haversine_km(listing.lat, listing.lng, school.lat, school.lng)
        maxd = f.max_distance_km or 5
        distance = 1.0 if distance_km <= maxd else max(0.25, 1 - (distance_km - maxd) / max(maxd, 3))
        if distance_km <= maxd:
            reasons.append(f"Cách {school.short_name} {distance_km:.1f} km".replace(".", ","))
    else:
        distance = 0.82

    have = set(listing.amenities or [])
    if f.amenities:
        got = [a for a in f.amenities if a in have]
        amen = len(got) / len(f.amenities)
        if got:
            reasons.append("Có " + ", ".join(AMENITY_LABEL[a].lower() for a in got[:3]) + " như bạn muốn")
    else:
        amen = min(1.0, 0.72 + 0.05 * len(have))

    safety = max(0.1, 1 - (listing.risk_score or 0) / 100)
    score = (
        WEIGHTS["budget"] * budget + WEIGHTS["distance"] * distance + WEIGHTS["amenities"] * amen + WEIGHTS["safety"] * safety
    )
    if f.room_types and listing.room_type not in f.room_types:
        score *= 0.85
    if f.max_people and listing.max_people and listing.max_people < f.max_people:
        score *= 0.85

    raw_text = f"{listing.title or ''} {listing.description or ''}"
    if is_all_inclusive_utilities(raw_text):
        reasons.append("Bao trọn gói chi phí điện nước")
    elif have and not f.amenities:
        top_am = [AMENITY_LABEL[a].lower() for a in listing.amenities[:3] if a in AMENITY_LABEL]
        if top_am:
            reasons.append("Trang bị " + ", ".join(top_am))

    st = stats.get(listing.district)
    if st and st["median"] and listing.price < st["median"] * 0.96 and listing.risk_level == "low":
        reasons.append(f"Rẻ hơn {round((1 - listing.price / st['median']) * 100)}% so với mặt bằng {listing.district}")
    elif st and st["median"] and listing.price <= st["median"] * 1.05 and listing.risk_level == "low":
        reasons.append(f"Giá hợp lý theo mặt bằng {listing.district}")

    if listing.risk_level == "low":
        reasons.append("Rủi ro thấp")

    return {
        "score": max(1, min(99, round(score * 100))),
        "breakdown": {k: round(v * 100) for k, v in {"budget": budget, "distance": distance, "amenities": amen, "safety": safety}.items()},
        "reasons": list(dict.fromkeys(reasons))[:4],
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
        "room_type_label": ROOM_TYPES.get(listing.room_type, "Phòng trọ"),
    }
