"""Gộp danh mục admin thêm (bảng catalog_items) vào danh mục gốc trong catalog.py.

Các module khác import AMENITIES, AMENITY_KEYS... theo tên, nên ở đây sửa tại chỗ
(không gán lại) để mọi nơi thấy cùng dữ liệu.
"""

import copy

from sqlalchemy.orm import Session

from . import catalog
from .models import CatalogItem

_BUILTIN_AMENITIES = copy.deepcopy(catalog.AMENITIES)
_BUILTIN_SCAM = list(catalog.SCAM_KEYWORDS)
BUILTIN_AMENITY_KEYS = {a["key"] for a in _BUILTIN_AMENITIES}
BUILTIN_SCAM = set(_BUILTIN_SCAM)


def builtin_synonyms(key: str) -> list[str]:
    return next((a["synonyms"] for a in _BUILTIN_AMENITIES if a["key"] == key), [])


def apply(db: Session) -> None:
    items = db.query(CatalogItem).all()
    amenities = copy.deepcopy(_BUILTIN_AMENITIES)
    by_key = {a["key"]: a for a in amenities}
    for it in items:
        if it.kind == "amenity" and it.key not in by_key:
            a = {"key": it.key, "label": it.label, "synonyms": list(it.data or [])}
            amenities.append(a)
            by_key[it.key] = a
    for it in items:
        if it.kind == "synonyms" and it.key in by_key:
            a = by_key[it.key]
            a["synonyms"] = list(dict.fromkeys([*a["synonyms"], *(it.data or [])]))

    catalog.AMENITIES[:] = amenities
    catalog.AMENITY_KEYS.clear()
    catalog.AMENITY_KEYS.update(by_key)
    catalog.AMENITY_LABEL.clear()
    catalog.AMENITY_LABEL.update({a["key"]: a["label"] for a in amenities})
    catalog.SCAM_KEYWORDS[:] = list(dict.fromkeys([*_BUILTIN_SCAM, *(it.key for it in items if it.kind == "scam_keyword")]))
