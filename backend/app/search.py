"""Tìm kiếm tin đăng: Elasticsearch (bộ phân tích tiếng Việt có/không dấu, geo_point) nếu đã cấu hình,
ngược lại lọc bằng SQL. Kết quả được xếp hạng lại theo mức phù hợp với nhu cầu sinh viên."""

import logging
import time

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .config import settings
from .geo import haversine_km
from .models import Listing, ListingSource, School
from .pricing import district_stats
from .query_parser import SearchFilters
from .recommend import match
from .serializers import card

log = logging.getLogger(__name__)
_es: dict = {"client": None, "checked": False, "last_attempt": 0.0}

INDEX_SETTINGS = {
    "analysis": {
        "filter": {"vi_fold": {"type": "asciifolding", "preserve_original": True}},
        "analyzer": {"vi": {"tokenizer": "standard", "filter": ["lowercase", "vi_fold"]}},
    }
}
INDEX_MAPPINGS = {
    "properties": {
        "title": {"type": "text", "analyzer": "vi"},
        "description": {"type": "text", "analyzer": "vi"},
        "address": {"type": "text", "analyzer": "vi"},
        "price": {"type": "integer"},
        "area": {"type": "float"},
        "district": {"type": "keyword"},
        "room_type": {"type": "keyword"},
        "amenities": {"type": "keyword"},
        "max_people": {"type": "integer"},
        "location": {"type": "geo_point"},
        "risk_score": {"type": "integer"},
        "status": {"type": "keyword"},
        "quality_score": {"type": "float"},
        "posted_at": {"type": "date"},
    }
}


def es():
    if not settings.elasticsearch_url:
        return None
    if _es["client"] is not None:
        return _es["client"]
    now = time.monotonic()
    if _es["checked"] and now - float(_es.get("last_attempt", 0.0)) < 15.0:
        return None
    _es["checked"] = True
    _es["last_attempt"] = now
    try:
        from elasticsearch import Elasticsearch

        client = Elasticsearch(settings.elasticsearch_url, request_timeout=5)
        if client.ping():
            if not client.indices.exists(index=settings.es_index):
                client.indices.create(index=settings.es_index, settings=INDEX_SETTINGS, mappings=INDEX_MAPPINGS)
            _es["client"] = client
    except Exception as exc:
        log.warning("Không kết nối được Elasticsearch (%s), dùng tìm kiếm SQL", exc)
    return _es["client"]


def to_doc(l: Listing) -> dict:
    return {
        "title": l.title,
        "description": l.description,
        "address": l.address,
        "price": l.price,
        "area": l.area,
        "district": l.district,
        "room_type": l.room_type,
        "amenities": l.amenities or [],
        "max_people": l.max_people,
        "location": {"lat": l.lat, "lon": l.lng} if l.lat and l.lng else None,
        "risk_score": l.risk_score,
        "status": l.status,
        "quality_score": l.quality_score,
        "posted_at": l.posted_at.isoformat(),
    }


def index_listing(l: Listing) -> None:
    c = es()
    if c:
        c.index(index=settings.es_index, id=str(l.id), document=to_doc(l))


def reindex_all(db: Session) -> int:
    c = es()
    if not c:
        return 0
    from elasticsearch import helpers

    rows = db.query(Listing).all()
    helpers.bulk(c, ({"_index": settings.es_index, "_id": str(l.id), "_source": to_doc(l)} for l in rows))
    c.indices.refresh(index=settings.es_index)
    return len(rows)


def _es_ids(f: SearchFilters, school: School | None) -> list[int] | None:
    c = es()
    if not c:
        return None
    flt: list[dict] = [{"term": {"status": "active"}}]
    rng: dict = {}
    if f.budget_min:
        rng["gte"] = f.budget_min
    if f.budget_max:
        rng["lte"] = f.budget_max
    if rng:
        flt.append({"range": {"price": rng}})
    if f.area_min:
        flt.append({"range": {"area": {"gte": f.area_min}}})
    if f.districts:
        flt.append({"terms": {"district": f.districts}})
    if f.room_types:
        flt.append({"terms": {"room_type": f.room_types}})
    for a in f.amenities:
        flt.append({"term": {"amenities": a}})
    if school and f.max_distance_km:
        flt.append({"geo_distance": {"distance": f"{f.max_distance_km}km", "location": {"lat": school.lat, "lon": school.lng}}})
    must = (
        [{"multi_match": {"query": f.keywords, "fields": ["title^2", "description", "address"]}}] if f.keywords else [{"match_all": {}}]
    )
    try:
        res = c.search(index=settings.es_index, query={"bool": {"filter": flt, "must": must}}, size=500, source=False)
        return [int(h["_id"]) for h in res["hits"]["hits"]]
    except Exception as exc:
        log.warning("Truy vấn ES lỗi (%s), dùng SQL", exc)
        return None


def _sql_candidates(db: Session, f: SearchFilters) -> list[Listing]:
    from .catalog import find_amenities, norm

    q = db.query(Listing).filter(Listing.status == "active")
    if f.budget_min:
        q = q.filter(Listing.price >= f.budget_min)
    if f.budget_max:
        q = q.filter(Listing.price <= f.budget_max)
    if f.area_min:
        q = q.filter(Listing.area >= f.area_min)
    if f.districts:
        q = q.filter(Listing.district.in_(f.districts))
    if f.room_types:
        q = q.filter(Listing.room_type.in_(f.room_types))
    rows = q.all()
    if f.keywords:
        nk = norm(f.keywords)
        rows = [
            r
            for r in rows
            if nk in norm(f"{r.title or ''} {r.address or ''} {r.street or ''} {r.description or ''}")
        ]
    if f.amenities:
        req = set(f.amenities)
        rows = [
            r
            for r in rows
            if req <= (set(r.amenities or []) | set(find_amenities(f"{r.title or ''}. {r.description or ''}")))
        ]
    return rows


def run_search(db: Session, f: SearchFilters, page: int = 1, page_size: int = 12) -> dict:
    school = db.get(School, f.school_id) if f.school_id else None
    ids = _es_ids(f, school)
    engine = "elasticsearch" if ids is not None else "sql"
    cands = db.query(Listing).filter(Listing.id.in_(ids)).all() if ids is not None else _sql_candidates(db, f)

    if school and f.max_distance_km:
        cands = [l for l in cands if l.lat and haversine_km(l.lat, l.lng, school.lat, school.lng) <= f.max_distance_km]
    if f.max_people:
        cands = [l for l in cands if not l.max_people or l.max_people >= f.max_people]

    hidden = [l for l in cands if f.hide_high_risk and l.risk_level == "high"]
    visible = [l for l in cands if not (f.hide_high_risk and l.risk_level == "high")]
    stats = district_stats(db)
    scored = [(l, match(l, f, school, stats)) for l in visible]

    if f.sort == "price_asc":
        scored.sort(key=lambda x: x[0].price)
    elif f.sort == "price_desc":
        scored.sort(key=lambda x: -x[0].price)
    elif f.sort == "newest":
        scored.sort(key=lambda x: x[0].posted_at, reverse=True)
    elif f.sort == "distance":
        scored.sort(key=lambda x: x[1]["distance_km"] if x[1]["distance_km"] is not None else 99)
    else:
        scored.sort(key=lambda x: (-x[1]["score"], x[0].price))

    ids_all = [l.id for l, _ in scored]
    source_names = (
        {s for (s,) in db.query(ListingSource.source_name).filter(ListingSource.listing_id.in_(ids_all)).distinct().all()} if ids_all else set()
    )
    start = (page - 1) * page_size
    return {
        "engine": engine,
        "total": len(scored),
        "page": page,
        "pages": max(1, -(-len(scored) // page_size)),
        "hidden_risky": len(hidden),
        "merged_duplicates": sum(max(0, l.source_count - 1) for l, _ in scored),
        "source_count": len(source_names),
        "items": [card(l, m, stats) for l, m in scored[start : start + page_size]],
        "pins": [{"id": l.id, "lat": l.lat, "lng": l.lng, "price": l.price} for l, _ in scored[:200] if l.lat],
        "school": {"id": school.id, "name": school.short_name, "lat": school.lat, "lng": school.lng} if school else None,
    }
