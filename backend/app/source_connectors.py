"""Connector helpers shared by crawler tasks and contract tests."""

import json
import re
from collections.abc import Iterable

import httpx

from .db import utcnow
from .pipeline import RawPost
from .url_safety import validate_public_http_url


DISTRICTS = {"son tra": "Sơn Trà", "ngu hanh son": "Ngũ Hành Sơn", "lien chieu": "Liên Chiểu", "hai chau": "Hải Châu", "thanh khe": "Thanh Khê", "cam le": "Cẩm Lệ", "hoa vang": "Hòa Vang"}
HELPRENT_STUDENT_TYPES = {"room", "studio", "apartment", "flat", "phòng", "căn hộ"}


def extract_helprent_detail_meta(html: str) -> dict:
    """Trích xuất danh sách ảnh thật, diện tích và mô tả từ trang chi tiết HelpRent."""
    images: list[str] = []
    area: float | None = None
    description: str = ""

    # 1. Mảng ảnh đầy đủ từ #lp-all-photos
    if m_photos := re.search(r'id=["\']lp-all-photos["\'][^>]*>\s*(\[.*?\])\s*</script>', html, re.S):
        try:
            arr = json.loads(m_photos.group(1))
            if isinstance(arr, list):
                images.extend(str(u).strip() for u in arr if str(u).strip().startswith("http"))
        except Exception:
            pass

    # 2. Schema.org JSON-LD (image, floorSize, description)
    for m_ld in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>\s*(\{.*?\})\s*</script>', html, re.S):
        try:
            ld = json.loads(m_ld.group(1))
            if not isinstance(ld, dict):
                continue
            ld_imgs = ld.get("image")
            if isinstance(ld_imgs, list):
                images.extend(str(u).strip() for u in ld_imgs if str(u).strip().startswith("http"))
            elif isinstance(ld_imgs, str) and ld_imgs.strip().startswith("http"):
                images.append(ld_imgs.strip())
            if area is None and isinstance(ld.get("floorSize"), dict):
                val = ld["floorSize"].get("value")
                if val is not None:
                    area = float(val)
            if not description and isinstance(ld.get("description"), str):
                description = ld["description"].strip()
        except Exception:
            pass

    # 3. Fallback og:image hoặc link /photo/\d+/
    if not images:
        for m_og in re.finditer(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html):
            u = m_og.group(1).strip()
            if u.startswith("http"):
                images.append(u)
        for m_ph in re.finditer(r"https://helprentdanang\.com/photo/\d+/", html):
            images.append(m_ph.group(0))

    dedup_images = list(dict.fromkeys(images))[:10]
    return {"images": dedup_images, "area": area, "description": description}


def rate_limit_delay(value: str) -> float:
    normalized = value.lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:yêu cầu|request).*?/\s*(?:(\d+(?:\.\d+)?)\s*)?(giây|phút|second|minute)", normalized)
    if not match:
        return 2.0
    requests = max(float(match.group(1)), 0.1)
    period = float(match.group(2) or 1)
    if match.group(3) in {"phút", "minute"}:
        period *= 60
    return round(max(0.5, period / requests), 2)


def normalize_helprent(item: dict, source_name: str) -> RawPost:
    district = DISTRICTS.get(str(item.get("district", "")).lower(), item.get("district") or "Đà Nẵng")
    price = int(item.get("price_month") or 0)
    furnished = "đầy đủ nội thất" if item.get("furnished") else "chưa xác định nội thất"
    area_val = item.get("area")
    area_part = f" Diện tích {float(area_val):g}m2." if area_val else ""
    desc_part = f" {item['description']}" if item.get("description") else ""
    text = (f"Cho thuê {item.get('type_label') or item.get('type') or 'phòng'} tại {district}, Đà Nẵng. "
            f"Giá {price:,.0f} đồng/tháng.{area_part} {item.get('bedrooms') or 0} phòng ngủ, {furnished}. "
            f"Tin thuê dài hạn từ nguồn {item.get('source') or source_name}.{desc_part}").replace(",", ".")
    raw_images = item.get("images") if isinstance(item.get("images"), list) else []
    return RawPost(
        source_name=source_name,
        url=validate_public_http_url(str(item["url"])),
        text=text,
        images=[str(u) for u in raw_images if str(u).startswith("http")],
    )


def is_helprent_student_housing(item: dict) -> bool:
    """Keep room-scale rentals the shared extractor can represent reliably."""
    category = str(item.get("type") or item.get("type_label") or "").strip().casefold()
    price = int(item.get("price_month") or 0)
    return category in HELPRENT_STUDENT_TYPES and 0 < price <= 30_000_000


def fetch_helprent(start_url: str, source_name: str, max_pages: int) -> Iterable[RawPost]:
    base = validate_public_http_url(start_url, resolve_dns=True)
    with httpx.Client(timeout=20, follow_redirects=False, headers={"User-Agent": "PhongOiResearchBot/1.0"}) as client:
        for page in range(1, min(max_pages, 5) + 1):
            response = client.get(base, params={"page": page, "page_size": 20})
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise ValueError("Phản hồi connector vượt giới hạn 2 MB")
            results = response.json().get("results")
            if not isinstance(results, list):
                raise ValueError("HelpRent API không trả về mảng results")
            for item in results:
                if isinstance(item, dict) and item.get("url") and is_helprent_student_housing(item):
                    enriched = dict(item)
                    if not enriched.get("images"):
                        try:
                            detail_url = validate_public_http_url(str(enriched["url"]), resolve_dns=False)
                            detail_resp = client.get(detail_url, timeout=10)
                            if detail_resp.status_code == 200:
                                meta = extract_helprent_detail_meta(detail_resp.text)
                                if meta["images"]:
                                    enriched["images"] = meta["images"]
                                if meta["area"] and not enriched.get("area"):
                                    enriched["area"] = meta["area"]
                                if meta["description"] and not enriched.get("description"):
                                    enriched["description"] = meta["description"]
                        except Exception:
                            pass
                    yield normalize_helprent(enriched, source_name)
            if not results:
                break


def apply_run_health(source, status: str) -> None:
    source.last_health_at = utcnow()
    if status == "success":
        source.health_score = 100
        source.consecutive_failures = 0
    elif status == "partial":
        source.health_score = 60
        source.consecutive_failures = 0
    else:
        source.health_score = 0
        source.consecutive_failures = int(source.consecutive_failures or 0) + 1
        if source.consecutive_failures >= 3:
            source.enabled = False
            source.status = "paused"
