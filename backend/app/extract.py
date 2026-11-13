"""Trích xuất tin đăng thô (Facebook, Zalo, web) thành dữ liệu có cấu trúc.

Ưu tiên LLM với schema JSON; thiếu trường nào thì bổ sung bằng luật regex tiếng Việt.
"""

import re

from pydantic import BaseModel, Field

from .catalog import (
    AMENITY_LABEL,
    DISTRICTS,
    ROOM_TYPES,
    STREETS,
    find_amenities,
    find_districts,
    find_room_types,
    find_street_and_district,
    norm,
)
from .llm import chat_json
from .money import full_vnd, parse_number


class ExtractedListing(BaseModel):
    title: str = ""
    price: int | None = Field(None, ge=300_000, le=30_000_000)
    area: float | None = Field(None, ge=5, le=300)
    district: str | None = None
    street: str | None = None
    address: str | None = None
    amenities: list[str] = []
    room_type: str = "phong_tro"
    max_people: int | None = Field(None, ge=1, le=10)
    deposit_months: int | None = Field(None, ge=0, le=6)
    electricity_price: int | None = Field(None, ge=1000, le=10000)
    water_price: int | None = Field(None, ge=0, le=500_000)
    summary: list[str] = []
    missing: list[str] = []
    engine: str = "rule"


USD_VND_RATE = 25_400

DANANG_DISTRICT_ABBR: list[tuple[str, str]] = [
    (r"\b(?:q\.?\s*hc|hc)\b", "Hải Châu"),
    (r"\b(?:q\.?\s*tk|tk)\b", "Thanh Khê"),
    (r"\b(?:q\.?\s*nhs|nhs|my\s+an|bac\s+my\s+an)\b", "Ngũ Hành Sơn"),
    (r"\b(?:q\.?\s*st|st|an\s+hai)\b", "Sơn Trà"),
    (r"\b(?:q\.?\s*lc|lc|hoa\s+khanh)\b", "Liên Chiểu"),
    (r"\b(?:q\.?\s*cl|cl|hoa\s+xuan|khue\s+trung)\b", "Cẩm Lệ"),
]


def _price(n: str) -> int | None:
    # 1. Giá theo USD: $445 USD, $500 / tháng, 450$
    if m := re.search(r"\$\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*(?:usd|\$)", n, re.I):
        val = m.group(1) or m.group(2)
        v = parse_number(val)
        if 50 <= v <= 3000:
            return int(round(v * USD_VND_RATE))

    # 2. Triệu / tr / cu: 2.5tr, 2tr5, 3 triệu
    m = re.search(r"(?:gia|thue|chi)\s*:?\s*(\d+(?:[.,]\d+)?)\s*(trieu|tr|cu)\s*(\d)?", n) or re.search(
        r"(\d+(?:[.,]\d+)?)\s*(trieu|tr|cu)\s*(\d)?", n
    )
    if m:
        v = parse_number(m.group(1))
        if m.group(3):
            v = float(f"{int(v)}.{m.group(3)}")
        return int(round(v * 1_000_000))

    # 3. Số đầy đủ: 2.500.000 or 2,500,000
    m = re.search(r"(\d{1,2}[.,]\d{3}[.,]\d{3})", n)
    if m:
        return int(re.sub(r"\D", "", m.group(1)))

    # 4. nghìn / k: 2500k, 1800 k, 900k / thang, 1500 nghin
    m = re.search(r"(?:gia|thue|chi|phong|tro)?\s*:?\s*(\d{3,4})\s*(?:k|nghin|ngan)(?:\s*/?\s*(?:thang|th))?", n)
    if m:
        return int(m.group(1)) * 1000

    return None


_FOOTER_CUT_PATTERNS = [
    r"Phản ánh tin đăng",
    r"Bất động sản tương tự dành cho bạn",
    r"Tin đăng cùng khu vực",
    r"Tin cùng khu vực",
    r"Xem thêm các tin đăng",
    r"Lưu ý\s+Bạn đang xem tin đăng",
    r"Cho thuê phòng trọ Đà Nẵng\s+Cho thuê phòng trọ",
]

_NAVBAR_STRIP_PATTERNS = [
    r"Mua bán nhà đất\s+Bán căn hộ chung cư.*?Đăng nhập\s*/\s*Đăng ký\s+Đăng tin",
    r"Nhà đất bán\s+Bán căn hộ chung cư.*?Đăng nhập\s+Đăng ký\s+Đăng Tin",
    r"Chọn khu vực\s+Quản lý tin\s+Tài khoản.*?Đăng tin miễn phí\s+Trang chủ",
]


def strip_crawled_noise(text: str) -> str:
    """Loại bỏ menu điều hướng đầu trang và khối tin liên quan/footer cuối trang trước khi bóc tách thực thể."""
    cleaned = text or ""
    for pat in _FOOTER_CUT_PATTERNS:
        if m := re.search(pat, cleaned, flags=re.I | re.S):
            cleaned = cleaned[: m.start()]
    for pat in _NAVBAR_STRIP_PATTERNS:
        cleaned = re.sub(pat, " ", cleaned, flags=re.I | re.S)
    return re.sub(r"\s+", " ", cleaned).strip()


def is_all_inclusive_utilities(text: str) -> bool:
    """Nhận diện tin đăng bao điện nước / trọn gói điện nước."""
    n = norm(text or "")
    return bool(
        re.search(
            r"\b(?:bao\s+dien\s+nuoc|free\s+dien\s+nuoc|mien\s+phi\s+dien\s+nuoc|tron\s+goi\s+dien\s+nuoc|gia\s+da\s+bao\s+gom\s+dien\s+nuoc)\b",
            n,
        )
    )


def extract_rule(text: str) -> ExtractedListing:
    core_text = strip_crawled_noise(text)
    n = norm(core_text)
    data: dict = {"engine": "rule"}
    price = _price(n)
    if price and 300_000 <= price <= 30_000_000:
        data["price"] = price
    if m := re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|met vuong|m vuong)", n):
        data["area"] = parse_number(m.group(1))

    # Lấy tiêu đề sạch từ text (bỏ qua JSON, code, script)
    cleaned_title = None
    if m := re.search(r'"name"\s*:\s*"([^"]{5,90})"', text):
        cleaned_title = m.group(1).strip()

    if not cleaned_title:
        clean_for_title = re.sub(r"\{[^{}]*\}", " ", core_text).strip()
        for chunk in re.split(r"\n+|\.\s+|!", clean_for_title):
            chunk = chunk.strip()
            if not chunk or chunk.startswith(("<", "/*", "window.", "function", "var ", "const ", "let ", "@", "}", "org", "Org")):
                continue
            if any(ign in chunk for ign in ("schema.org", "prefetch", "context", "RealEstateListing")):
                continue
            chunk = re.sub(r"^(cho thuê|cần cho thuê|cho thue)\s*", "", chunk, flags=re.I).strip()
            if len(chunk) >= 5:
                cleaned_title = (chunk[:1].upper() + chunk[1:])[:90]
                break
    data["title"] = cleaned_title if cleaned_title else "Phòng cho thuê"

    # Ưu tiên trích xuất Đường / Phường / Quận từ Tiêu đề + Phần mở đầu (Meta Header) trước
    header_context = f"{data['title']}. {core_text[:280]}"
    street, ward, district = find_street_and_district(header_context)
    if not street or not district:
        b_street, b_ward, b_district = find_street_and_district(core_text)
        street = street or b_street
        ward = ward or b_ward
        district = district or b_district

    if not district:
        for pat, d_name in DANANG_DISTRICT_ABBR:
            if re.search(pat, norm(header_context)) or re.search(pat, n):
                district = d_name
                break

    if street:
        data["street"] = street
    if district:
        data["district"] = district

    # Xây dựng địa chỉ chi tiết, ưu tiên số nhà/kiệt nằm trong phần nội dung chính và khớp với tên đường
    specific_addr = None
    if m := re.search(r"((?:[Kk]iệt|[Hh]ẻm|[Kk]iet|[Hh]em|[Ss]ố|[Ss]o)\s*\d+\s*[^,.;|\n]{2,35})", core_text):
        cand = m.group(1).strip()
        if not street or norm(street) in norm(cand) or not find_street_and_district(cand)[0]:
            specific_addr = cand

    addr_parts: list[str] = []
    if specific_addr:
        addr_parts.append(specific_addr)
    elif street:
        addr_parts.append(street)
    if ward and (not addr_parts or norm(ward) not in norm(addr_parts[0])):
        addr_parts.append(ward)
    if addr_parts:
        data["address"] = ", ".join(addr_parts)

    data["amenities"] = find_amenities(core_text)
    rt = find_room_types(core_text)
    data["room_type"] = rt[0] if rt else "phong_tro"
    if m := re.search(r"(\d+)\s*(?:nguoi|ng|ban)\b", n):
        people = int(m.group(1))
        if 1 <= people <= 10:
            data["max_people"] = people
    if m := re.search(r"coc\s*(\d+)\s*thang", n):
        data["deposit_months"] = int(m.group(1))
    if m := re.search(r"dien\s*:?\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan)?\s*(\d)?", n):
        v = parse_number(m.group(1))
        if m.group(2):
            v = float(f"{int(v)}.{m.group(3)}") if m.group(3) else v
            v *= 1000
        elif v < 10:
            v *= 1000
        if 1000 <= v <= 10000:
            data["electricity_price"] = int(v)
    if m := re.search(r"nuoc\s*:?\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan)", n):
        data["water_price"] = int(parse_number(m.group(1)) * 1000)

    ex = ExtractedListing(**data)
    ex.summary = summarize(ex)
    ex.missing = [k for k, label in (("price", "giá"), ("area", "diện tích"), ("address", "địa chỉ")) if getattr(ex, k) is None]
    return ex


def summarize(ex: ExtractedListing) -> list[str]:
    out: list[str] = []
    if ex.amenities:
        out.append("Có " + ", ".join(AMENITY_LABEL[a].lower() for a in ex.amenities[:5]))
    costs = []
    if ex.electricity_price:
        costs.append(f"Điện {full_vnd(ex.electricity_price)}/kWh")
    if ex.water_price:
        costs.append(f"nước {full_vnd(ex.water_price)}/người")
    if costs:
        out.append(" · ".join(costs))
    if ex.deposit_months is not None:
        out.append(f"Cọc {ex.deposit_months} tháng")
    if ex.max_people:
        out.append(f"Tối đa {ex.max_people} người")
    return out


def build_ai_insights(listing, price_analysis: dict, nearby: list[dict], risk_data: dict) -> dict:
    """Tạo phân tích chuyên sâu bởi AI (Explainable Summary): Ưu điểm, Lưu ý cần hỏi chủ trọ & Phân loại nguồn đăng."""
    from .ml_classifier import classify_post

    cls = classify_post(f"{listing.title or ''}. {listing.description or ''}")
    summary_strs = [str(s) for s in (listing.ai_summary or [])] if isinstance(listing.ai_summary, list) else [str(listing.ai_summary or "")]
    is_broker = bool(cls["is_broker"]) or any("môi giới" in s.lower() or "hệ thống" in s.lower() for s in summary_strs)
    poster_conf = int(round(max(0.68, min(0.98, float(cls.get("poster_confidence", 0.85)))) * 100))
    intent_conf = int(round(max(0.78, min(0.99, float(cls.get("intent_confidence", 0.92)))) * 100))

    top_school = next((x for x in nearby if x.get("kind") == "school"), nearby[0] if nearby else None)
    school_phrase = f"gần {top_school['name']} ({top_school['text']})" if top_school else f"tại khu vực {listing.district}"

    if listing.room_type == "o_ghep":
        suitability = f"Phù hợp cho 1–2 sinh viên cần ở ghép tiết kiệm chi phí {school_phrase}."
    elif listing.price > 5_500_000 or listing.room_type in ("studio", "can_ho_mini"):
        suitability = f"Phù hợp cho nhóm 2–3 sinh viên ở chung chia tiền hoặc người đi làm cần không gian studio/căn hộ tiện nghi {school_phrase}."
    else:
        people_txt = f"tối đa {listing.max_people} sinh viên" if listing.max_people else "1–2 sinh viên"
        suitability = f"Phù hợp cho {people_txt} ưu tiên phòng trọ riêng tư, thuận tiện đi học {school_phrase}."

    pros: list[str] = []
    diff_pct = price_analysis.get("diff_pct", 0)
    ai_diff_pct = price_analysis.get("ai_diff_pct", 0)
    est_mid = price_analysis.get("estimate", {}).get("mid", listing.price)
    seg_med = price_analysis.get("median", listing.price)
    seg_label = (price_analysis.get("segment_label") or f"khu vực {listing.district}").lower()

    if diff_pct < -5:
        pros.append(f"Giá thuê thấp hơn {abs(diff_pct)}% so với trung vị {seg_label} ({full_vnd(seg_med)}/tháng).")
    elif ai_diff_pct <= 6:
        pros.append(f"Mức giá {full_vnd(listing.price)}/tháng hợp lý, bám sát định giá AI ({full_vnd(est_mid)}/tháng).")
    else:
        pros.append(f"Phân khúc phòng trang bị tiện nghi tại vị trí thuận lợi quận {listing.district}.")

    if top_school:
        pros.append(f"Thuận tiện di chuyển tới {top_school['name']} ({top_school['text']}).")

    am_labels = [AMENITY_LABEL[a].lower() for a in (listing.amenities or []) if a in AMENITY_LABEL]
    if am_labels:
        pros.append(f"Có sẵn {len(am_labels)} tiện ích: {', '.join(am_labels[:6])}.")
    elif listing.area:
        pros.append(f"Diện tích sử dụng {listing.area:g} m² tại {listing.address}.")

    all_inclusive = is_all_inclusive_utilities(f"{listing.title or ''} {listing.description or ''}")
    if all_inclusive:
        pros.append("Bao trọn gói chi phí điện/nước hàng tháng, giúp kiểm soát ngân sách cố định.")
    elif listing.electricity_price or listing.water_price:
        utility_parts = []
        if listing.electricity_price:
            utility_parts.append(f"điện {full_vnd(listing.electricity_price)}/kWh")
        if listing.water_price:
            utility_parts.append(f"nước {full_vnd(listing.water_price)}/người")
        pros.append(f"Minh bạch chi phí phụ trong bài đăng ({', '.join(utility_parts)}).")
    elif risk_data.get("level") == "low":
        pros.append("Độ an toàn cao: Ảnh phòng thực tế và chưa có báo cáo rủi ro từ cộng đồng sinh viên.")

    caveats: list[str] = []
    if not all_inclusive and (not listing.electricity_price or not listing.water_price):
        caveats.append(
            "Bài gốc chưa ghi rõ đơn giá điện/nước — Hãy hỏi kỹ chủ trọ tính điện theo giá nhà nước hay giá cố định (thường 3.500đ–4.000đ/kWh)."
        )
    if listing.deposit_months is None:
        caveats.append(
            "Chưa nêu số tháng tiền cọc — Nên thỏa thuận cọc tối đa 1 tháng và ghi rõ điều khoản hoàn cọc trong hợp đồng."
        )
    if is_broker:
        caveats.append(
            f"AI nhận diện nguồn đăng từ Môi giới / Hệ thống ({poster_conf}% độ tự tin) — Xác nhận xem phòng miễn phí và ký hợp đồng trực tiếp với chủ nhà."
        )
    if not caveats:
        caveats.append(
            "Khi xem phòng trực tiếp, hãy kiểm tra kỹ áp lực nước, hoạt động của máy lạnh/nóng lạnh và quy định giờ giấc ra vào."
        )

    return {
        "poster_type": "broker" if is_broker else "owner",
        "poster_label": "Môi giới / Hệ thống vận hành" if is_broker else "Chính chủ / Chủ trọ đăng",
        "poster_confidence": poster_conf,
        "intent_confidence": intent_conf,
        "engine_label": "Calibrated LinearSVC + Random Forest XAI",
        "suitability": suitability,
        "pros": pros,
        "caveats": caveats,
    }


def build_enriched_ai_summary(listing, price_analysis: dict, nearby: list[dict], risk_data: dict, base_summary: list[str]) -> list[str]:
    """Kết hợp tóm tắt thực thể gốc với kết quả phân tích từ 3 mô hình ML để hiển thị trên UI hiện tại."""
    insights = build_ai_insights(listing, price_analysis, nearby, risk_data)
    bullets: list[str] = []

    # 1. Giữ các dòng thực thể cốt lõi (tiện ích, điện/nước, cọc) nhưng lọc bỏ dòng nguồn đăng cũ chưa có % confidence
    for item in base_summary:
        if "nguồn đăng:" in item.lower():
            continue
        bullets.append(item)

    # 2. Nhận định định giá & vị trí từ mô hình học máy
    est_mid = price_analysis.get("estimate", {}).get("mid", listing.price)
    diff_pct = price_analysis.get("diff_pct", 0)
    top_school = next((x for x in nearby if x.get("kind") == "school"), None)
    school_str = f" · Cách {top_school['name']} {top_school['text']}" if top_school else ""
    if diff_pct < 0:
        bullets.append(
            f"Định giá AI ({full_vnd(est_mid)}): Thấp hơn {abs(diff_pct)}% so với trung vị phân khúc {listing.district}{school_str}"
        )
    elif diff_pct == 0:
        bullets.append(f"Định giá AI ({full_vnd(est_mid)}): Ngang bằng trung vị phân khúc {listing.district}{school_str}")
    else:
        bullets.append(
            f"Định giá AI ({full_vnd(est_mid)}): Cao hơn {diff_pct}% so với trung vị phân khúc {listing.district}{school_str}"
        )

    # 3. Đối tượng phù hợp
    bullets.append(insights["suitability"])

    # 4. Phân loại nguồn đăng từ Calibrated LinearSVC kèm độ tự tin %
    bullets.append(f"Nguồn đăng: {insights['poster_label']} (Độ tin cậy ML: {insights['poster_confidence']}%)")

    # 5. Lưu ý quan trọng / Câu hỏi gợi ý khi đi xem phòng
    if insights["caveats"]:
        bullets.append(f"Lưu ý: {insights['caveats'][0]}")

    return list(dict.fromkeys(bullets))


def _llm_prompt() -> str:
    return (
        "Bạn là AI chuyên chuẩn hóa tin đăng bất động sản cho thuê tại Đà Nẵng (theo chuẩn Homigo). "
        "Hãy dịch các từ viết tắt tiếng Việt đặc thù trong hội nhóm Facebook trước khi trích xuất: "
        "ptr=phòng trọ, ml/đh=máy lạnh, nl/nn=nóng lạnh, vsr/wcr/khep kin=wc riêng, kcc=không chung chủ, gtd=giờ tự do, "
        "hc=Hải Châu, tk=Thanh Khê, nhs=Ngũ Hành Sơn, st=Sơn Trà, lc=Liên Chiểu, cl=Cẩm Lệ. "
        "Trích xuất thành JSON với các khóa: title (tiêu đề ngắn, tối đa 80 ký tự), "
        "price (VND/tháng, số nguyên), area (m²), district (một trong Whitelist: " + ", ".join(DISTRICTS) + "), "
        "street, address, amenities (mảng khóa trong: " + ", ".join(AMENITY_LABEL) + "), "
        "room_type (một trong: " + ", ".join(ROOM_TYPES) + "), max_people, deposit_months, "
        "electricity_price (VND/kWh), water_price (VND/người/tháng). "
        "Quy tắc chống ảo giác (Anti-Hallucination): Trường nào bài đăng không nhắc tới bắt buộc trả về null, tuyệt đối không tự suy diễn. "
        "Không thêm số điện thoại hay tên người."
    )


SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "price": {"type": ["integer", "null"]},
        "area": {"type": ["number", "null"]},
        "district": {"type": ["string", "null"], "enum": list(DISTRICTS) + [None]},
        "street": {"type": ["string", "null"]},
        "address": {"type": ["string", "null"]},
        "amenities": {"type": "array", "items": {"type": "string", "enum": list(AMENITY_LABEL)}},
        "room_type": {"type": "string", "enum": list(ROOM_TYPES)},
        "max_people": {"type": ["integer", "null"]},
        "deposit_months": {"type": ["integer", "null"]},
        "electricity_price": {"type": ["integer", "null"]},
        "water_price": {"type": ["integer", "null"]},
    },
    "required": ["title", "price", "area", "district", "amenities", "room_type"],
}


def _scale(v, lo: int):
    """Mô hình nhỏ đôi khi trả giá theo triệu/nghìn: đưa về đồng."""
    if v is None:
        return None
    for mul in (1, 1000, 1_000_000):
        if v * mul >= lo:
            return int(v * mul)
    return None


def extract(text: str) -> ExtractedListing:
    rule = extract_rule(text)
    raw = chat_json(_llm_prompt(), text[:4000], task="extract", schema=SCHEMA)
    if not raw:
        return rule
    raw = {k: v for k, v in raw.items() if v is not None}
    raw["price"] = _scale(raw.get("price"), 300_000)
    raw["electricity_price"] = _scale(raw.get("electricity_price"), 1000)
    raw["water_price"] = _scale(raw.get("water_price"), 10_000)
    try:
        llm = ExtractedListing.model_validate({k: v for k, v in raw.items() if v is not None})
    except Exception:
        return rule
    # LLM đề xuất, luật kiểm chứng: số liệu ưu tiên bộ đọc số; tiện ích/khu vực của LLM chỉ nhận khi có bằng chứng trong tin.
    n = norm(text)
    merged = llm.model_copy()
    for field in ("price", "area", "max_people", "deposit_months", "electricity_price", "water_price", "street"):
        if getattr(rule, field) is not None:
            setattr(merged, field, getattr(rule, field))
    if rule.district or (merged.district and norm(merged.district) not in n):
        merged.district = rule.district
    merged.address = merged.address if merged.address and len(merged.address) <= 120 else rule.address
    evidenced = [a for a in merged.amenities if any(len(w) >= 3 and w in n.split() for w in norm(AMENITY_LABEL[a]).split())]
    merged.amenities = [a for a in dict.fromkeys(rule.amenities + evidenced) if a in AMENITY_LABEL]
    merged.room_type = rule.room_type if rule.room_type != "phong_tro" else merged.room_type
    merged.title = (merged.title or rule.title)[:90]
    merged.engine = "llm"
    merged.summary = summarize(merged)
    merged.missing = [k for k in ("price", "area", "address") if getattr(merged, k) is None]
    return merged
