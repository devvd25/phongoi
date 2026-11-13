import ast
from typing import Any

from .catalog import AMENITY_LABEL, ROOM_TYPES
from .models import Listing

JUNK_IMAGE_PATTERNS = (
    "facebook.com/tr",
    "ev=pageview",
    "noscript=1",
    "google-analytics",
    "googletagmanager",
    "doubleclick",
    "data:image",
    "svg+xml",
    "%3csvg",
    ".svg",
    "spacer.gif",
    "blank.gif",
    "placeholder",
    "openmap.png",
    "default.jpg",
    "default.png",
    "no-image",
    "noimage",
)


def clean_listing_images(raw: Any) -> list[str]:
    """Loại bỏ ảnh tracking pixel (Facebook Pixel, GA), ảnh SVG rỗng, bản đồ tĩnh và ảnh mặc định."""
    if not raw or not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        u = item.strip()
        if not u or not u.startswith(("http://", "https://", "/")):
            continue
        lower = u.lower()
        if any(pat in lower for pat in JUNK_IMAGE_PATTERNS):
            continue
        if u not in out:
            out.append(u)
    return out



def normalize_ai_summary(raw: Any) -> list[str]:
    """Đảm bảo ai_summary luôn là list[str], tự động khôi phục dữ liệu cũ bị lưu dạng chuỗi."""
    if not raw:
        return []
    items: list[str] = []
    if isinstance(raw, list):
        for elem in raw:
            items.extend(normalize_ai_summary(elem))
    elif isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        if s.startswith("[") and "]" in s:
            bracket_end = s.find("]")
            list_part = s[: bracket_end + 1]
            tail_part = s[bracket_end + 1 :].lstrip(" ·,-")
            try:
                parsed = ast.literal_eval(list_part)
                if isinstance(parsed, list):
                    items.extend(str(x).strip() for x in parsed if str(x).strip())
                else:
                    items.append(list_part)
            except Exception:
                items.append(list_part.strip("[]'\" "))
            if tail_part:
                items.extend(p.strip() for p in tail_part.split(" · ") if p.strip())
        else:
            items.extend(p.strip() for p in s.split(" · ") if p.strip())
    else:
        val = str(raw).strip()
        if val:
            items.append(val)
    return list(dict.fromkeys(x for x in items if x))



def price_tag(listing: Listing, stats: dict | None) -> str | None:
    s = (stats or {}).get(listing.district)
    if not s or not s["median"]:
        return None
    if listing.price <= s["median"] * 0.95:
        return "Giá tốt"
    if listing.price >= s["median"] * 1.15:
        return "Giá cao"
    return None


def card(listing: Listing, m: dict | None = None, stats: dict | None = None) -> dict:
    meta = [f"{listing.area:g} m²".replace(".", ",") if listing.area else None]
    feature = next((AMENITY_LABEL[a] for a in (listing.amenities or []) if a in ("gac_lung", "ban_cong", "may_giat", "nau_an")), None)
    meta.append(feature or ROOM_TYPES.get(listing.room_type))
    if m and m.get("distance_km") is not None:
        meta.append(f"{m['distance_km']:.1f} km".replace(".", ","))
    return {
        "id": listing.id,
        "title": listing.title,
        "price": listing.price,
        "area": listing.area,
        "district": listing.district,
        "street": listing.street,
        "address": listing.address,
        "short_address": f"{listing.street}, {listing.district}" if listing.street else listing.district,
        "lat": listing.lat,
        "lng": listing.lng,
        "image": (clean_listing_images(listing.images) or [None])[0],
        "images": clean_listing_images(listing.images),
        "room_type": listing.room_type,
        "room_type_label": ROOM_TYPES.get(listing.room_type, "Phòng trọ"),
        "amenities": listing.amenities or [],
        "amenity_labels": [AMENITY_LABEL[a] for a in (listing.amenities or []) if a in AMENITY_LABEL],
        "max_people": listing.max_people,
        "risk_level": listing.risk_level,
        "risk_score": listing.risk_score,
        "quality_score": listing.quality_score,
        "source_count": listing.source_count,
        "status": listing.status,
        "posted_at": listing.posted_at.isoformat() + "Z",
        "meta": " · ".join(x for x in meta if x),
        "price_tag": price_tag(listing, stats),
        "match": m["score"] if m else None,
        "match_breakdown": m["breakdown"] if m else None,
        "reasons": m["reasons"] if m else [],
        "distance_km": m["distance_km"] if m else None,
    }
