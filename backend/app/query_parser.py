"""Hiểu câu tìm kiếm tự nhiên -> bộ lọc có cấu trúc.

Luồng như thuyết minh: LLM nhận ngữ cảnh chỉ mục (khu vực, trường, tiện ích hợp lệ) và sinh tham số
lọc; backend kiểm tra bằng Pydantic rồi mới dựng truy vấn. Không có LLM hoặc LLM trả sai thì dùng
bộ phân tích luật tiếng Việt bên dưới.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from .catalog import (
    AMENITY_KEYS,
    AMENITY_LABEL,
    DISTRICTS,
    ROOM_TYPES,
    find_amenities,
    find_districts,
    find_room_types,
    find_street_and_district,
    norm,
)
from .llm import chat_json
from .models import School
from .money import parse_number, short_vnd


class SearchFilters(BaseModel):
    budget_min: int | None = Field(None, ge=0, le=50_000_000)
    budget_max: int | None = Field(None, ge=0, le=50_000_000)
    area_min: float | None = Field(None, ge=0, le=500)
    districts: list[str] = []
    school_id: int | None = None
    max_distance_km: float | None = Field(None, gt=0, le=50)
    amenities: list[str] = []
    room_types: list[str] = []
    max_people: int | None = Field(None, ge=1, le=10)
    keywords: str | None = None
    hide_high_risk: bool = True
    sort: Literal["match", "price_asc", "price_desc", "newest", "distance"] = "match"

    @field_validator("districts")
    @classmethod
    def _known_districts(cls, v: list[str]) -> list[str]:
        return [d for d in v if d in DISTRICTS]

    @field_validator("amenities")
    @classmethod
    def _known_amenities(cls, v: list[str]) -> list[str]:
        return [a for a in dict.fromkeys(v) if a in AMENITY_KEYS]

    @field_validator("room_types")
    @classmethod
    def _known_room_types(cls, v: list[str]) -> list[str]:
        return [r for r in v if r in ROOM_TYPES]


_UNIT = r"(trieu|tr|cu|k|nghin|ngan|m(?![2²]))?"
_MONEY = rf"(\d+(?:[.,]\d+)?)\s*{_UNIT}\s*(\d)?"


def _money(val: str, unit: str | None, tail: str | None) -> int:
    v = parse_number(val)
    if unit in ("k", "nghin", "ngan"):
        return int(v * 1000)
    if tail and unit in ("tr", "trieu", "cu", "m"):
        v = float(f"{int(v)}.{tail}")
    if unit in ("tr", "trieu", "cu", "m") or (unit is None and v < 100):
        return int(round(v * 1_000_000))
    return int(v)


def parse_rule(query: str, schools: list[School]) -> SearchFilters:
    n = norm(query)
    data: dict = {}

    if m := re.search(r"(\d+(?:[.,]\d+)?)\s*(?:trieu|tr)?\s*(?:-|den|toi|~)\s*(\d+(?:[.,]\d+)?)\s*(?:trieu|tr)\b", n):
        data["budget_min"] = int(parse_number(m.group(1)) * 1_000_000)
        data["budget_max"] = int(parse_number(m.group(2)) * 1_000_000)
    elif m := re.search(r"(?:duoi|toi da|khong qua|max|re hon|it hon|nho hon|<=?)\s*" + _MONEY, n):
        data["budget_max"] = _money(m.group(1), m.group(2), m.group(3))
    elif m := re.search(r"(?:duoi|toi da|khong qua|khoang|tam|chung)?\s*(\d+)\s*(?:trieu|tr|cu)\s*ruoi", n):
        # "1 triệu rưỡi" = 1,5 triệu
        mid = (int(m.group(1)) + 0.5) * 1_000_000
        data["budget_min"], data["budget_max"] = (None, int(mid)) if re.search(r"duoi|toi da|khong qua", m.group(0)) else (int(mid * 0.85), int(mid * 1.15))
    elif m := re.search(r"(?:khoang|tam|chung)\s*" + _MONEY, n):
        mid = _money(m.group(1), m.group(2), m.group(3))
        data["budget_min"], data["budget_max"] = int(mid * 0.85), int(mid * 1.15)
    elif m := re.search(r"(\d+(?:[.,]\d+)?)\s*(trieu|tr)\s*(\d)?", n):
        data["budget_max"] = int(_money(m.group(1), m.group(2), m.group(3)) * 1.1)
    if m := re.search(r"(?:tren|toi thieu|it nhat|>=?)\s*" + _MONEY, n):
        data["budget_min"] = _money(m.group(1), m.group(2), m.group(3))

    if m := re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|met vuong|m vuong)", n):
        data["area_min"] = round(parse_number(m.group(1)) * 0.9, 1)
    if m := re.search(r"(\d+(?:[.,]\d+)?)\s*km", n):
        data["max_distance_km"] = parse_number(m.group(1))
    if m := re.search(r"(\d+)\s*(?:nguoi|ng)\b", n):
        data["max_people"] = int(m.group(1))

    for s in schools:
        if any(re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", n) for a in s.aliases):
            data["school_id"] = s.id
            data.setdefault("max_distance_km", 3.0 if "gan" in n else 5.0)
            break

    street, ward, s_district = find_street_and_district(query)
    districts = find_districts(query)
    if s_district and s_district not in districts:
        districts.append(s_district)
    data["districts"] = districts
    data["amenities"] = find_amenities(query)
    data["room_types"] = find_room_types(query)
    if street:
        data["keywords"] = street
    elif "bao dien nuoc" in n or "free dien nuoc" in n:
        data["keywords"] = "bao điện nước"
    elif "bien" in n.split():
        data["keywords"] = "biển"
    return SearchFilters(**data)


def _llm_prompt(schools: list[School]) -> str:
    school_list = "; ".join(f"{s.id}={s.name}" for s in schools)
    amenity_list = "; ".join(f"{k}={v}" for k, v in AMENITY_LABEL.items())
    return (
        "Bạn là bộ phân tích truy vấn tìm phòng trọ tại Đà Nẵng cho sinh viên. Chỉ trả về JSON, không giải thích.\n"
        "budget_min, budget_max: số nguyên tính bằng ĐỒNG (VND), ví dụ 2tr5 = 2500000, 1 triệu rưỡi = 1500000.\n"
        f"districts: chỉ ghi khu vực người dùng NÓI RÕ, chọn trong: {', '.join(DISTRICTS)}.\n"
        f"school_id: chọn trong {school_list}; không nhắc trường thì null.\n"
        f"amenities: chỉ ghi tiện ích người dùng NÓI RÕ, khóa trong: {amenity_list}.\n"
        f"room_types: chỉ ghi khi người dùng nói rõ loại phòng, chọn trong: {', '.join(ROOM_TYPES)}.\n"
        "keywords: chỉ 1–3 từ đặc biệt không thuộc các trường trên (ví dụ 'biển'), không chép lại cả câu.\n"
        "Không biết thì để null hoặc mảng rỗng, KHÔNG liệt kê tất cả giá trị.\n"
        'Ví dụ: "phòng dưới 2tr5 gần bách khoa có gác" -> {"budget_min":null,"budget_max":2500000,"area_min":null,"districts":[],'
        '"school_id":1,"max_distance_km":3,"amenities":["gac_lung"],"room_types":[],"max_people":null,"keywords":null}\n'
        'Ví dụ: "ở ghép 2 người Hải Châu tầm 1 triệu rưỡi" -> {"budget_min":1300000,"budget_max":1700000,"area_min":null,'
        '"districts":["Hải Châu"],"school_id":null,"max_distance_km":null,"amenities":[],"room_types":["o_ghep"],"max_people":2,"keywords":null}'
    )


def _mentioned(label: str, n: str) -> bool:
    """Có bằng chứng trong câu: một từ (≥3 ký tự) của nhãn xuất hiện trong câu đã chuẩn hóa."""
    return any(len(w) >= 3 and re.search(rf"\b{re.escape(w)}\b", n) for w in norm(label).split())


def reconcile(llm: SearchFilters, rule: SearchFilters, query: str) -> SearchFilters:
    """LLM đề xuất, luật kiểm chứng: số liệu ưu tiên bộ đọc số; giá trị phân loại chỉ nhận khi có bằng chứng trong câu."""
    n = norm(query)
    f = llm.model_copy()
    for k in ("budget_min", "budget_max"):
        v = getattr(f, k)
        if v is not None and v < 100:
            v *= 1_000_000  # mô hình nhỏ hay trả "2.5" (triệu)
        elif v is not None and v < 100_000:
            v *= 1000  # hoặc "2500" (nghìn)
        setattr(f, k, getattr(rule, k) if getattr(rule, k) is not None else (int(v) if v else None))
    if f.budget_min and f.budget_max and f.budget_min > f.budget_max:
        f.budget_min = None
    f.area_min = rule.area_min if rule.area_min is not None else f.area_min
    f.districts = list(dict.fromkeys(rule.districts + [d for d in f.districts if norm(d) in n]))
    f.amenities = list(dict.fromkeys(rule.amenities + [a for a in f.amenities if _mentioned(AMENITY_LABEL[a], n)]))
    f.room_types = rule.room_types or [r for r in f.room_types if r != "phong_tro" and _mentioned(ROOM_TYPES[r], n)][:1]
    f.school_id = rule.school_id or f.school_id
    f.max_distance_km = rule.max_distance_km if rule.max_distance_km else (f.max_distance_km or 3.0) if f.school_id else None
    f.max_people = rule.max_people or f.max_people
    if f.keywords and (len(f.keywords.split()) > 3 or norm(f.keywords) not in n):
        f.keywords = None
    f.keywords = rule.keywords or f.keywords
    return f


def _schema(schools: list[School]) -> dict:
    """JSON schema kèm danh sách giá trị hợp lệ, để LLM (kể cả mô hình nhỏ chạy cục bộ) chỉ chọn trong ngữ cảnh chỉ mục."""
    num = {"type": ["number", "null"]}
    integer = {"type": ["integer", "null"]}
    return {
        "type": "object",
        "properties": {
            "budget_min": integer,
            "budget_max": integer,
            "area_min": num,
            "districts": {"type": "array", "items": {"type": "string", "enum": list(DISTRICTS)}},
            "school_id": {"type": ["integer", "null"], "enum": [s.id for s in schools] + [None]},
            "max_distance_km": num,
            "amenities": {"type": "array", "items": {"type": "string", "enum": list(AMENITY_LABEL)}},
            "room_types": {"type": "array", "items": {"type": "string", "enum": list(ROOM_TYPES)}},
            "max_people": integer,
            "keywords": {"type": ["string", "null"]},
        },
        "required": ["budget_min", "budget_max", "area_min", "districts", "school_id", "max_distance_km", "amenities", "room_types", "max_people", "keywords"],
    }


def chips(f: SearchFilters, schools: list[School]) -> list[str]:
    out: list[str] = []
    if f.budget_min and f.budget_max:
        out.append(f"{short_vnd(f.budget_min)} – {short_vnd(f.budget_max)}")
    elif f.budget_max:
        out.append(f"Giá ≤ {short_vnd(f.budget_max)}")
    elif f.budget_min:
        out.append(f"Giá ≥ {short_vnd(f.budget_min)}")
    if f.school_id:
        s = next((s for s in schools if s.id == f.school_id), None)
        if s:
            out.append(f"Cách {s.short_name} ≤ {f.max_distance_km or 5:g} km".replace(".", ","))
    out += f.districts
    out += [ROOM_TYPES[r] for r in f.room_types]
    out += [AMENITY_LABEL[a] for a in f.amenities]
    if f.area_min:
        out.append(f"Từ {round(f.area_min / 0.9):d} m²")
    if f.max_people:
        out.append(f"{f.max_people} người")
    if f.keywords:
        out.append(f"“{f.keywords}”")
    return out


def parse_query(query: str, db: Session) -> tuple[SearchFilters, list[str], str]:
    schools = db.query(School).all()
    raw = chat_json(_llm_prompt(schools), query, task="query", schema=_schema(schools))
    rule = parse_rule(query, schools)
    engine, filters = "rule", rule
    if raw:
        try:
            filters = reconcile(SearchFilters.model_validate(raw), rule, query)
            engine = "llm"
        except Exception:
            filters = rule
    return filters, chips(filters, schools), engine
