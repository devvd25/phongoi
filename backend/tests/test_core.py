import os

os.environ["DATABASE_URL"] = "sqlite:///./test_phongoi.db"
os.environ["LLM_PROVIDER"] = "none"  # kiểm thử phần luật, không phụ thuộc Ollama đang chạy hay không

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app import seed  # noqa: E402
from app.extract import extract_rule  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CrawlRun, CrawlSource, School  # noqa: E402
from app.query_parser import parse_rule  # noqa: E402

SCHOOLS = [School(id=i + 1, **s) for i, s in enumerate(seed.SCHOOLS)]


@pytest.fixture(scope="module")
def client():
    seed.run()
    return TestClient(app)


def token(client, email, pw):
    return {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": email, "password": pw}).json()["token"]}


@pytest.mark.parametrize(
    "q,expect",
    [
        ("phòng dưới 2tr5 gần bách khoa có gác", {"budget_max": 2_500_000, "school_id": 1, "amenities": ["gac_lung"]}),
        ("phong duoi 2 trieu o ghep 2 nguoi", {"budget_max": 2_000_000, "room_types": ["o_ghep"], "max_people": 2}),
        ("từ 2 đến 3 triệu Hải Châu có máy lạnh", {"budget_min": 2_000_000, "budget_max": 3_000_000, "districts": ["Hải Châu"], "amenities": ["may_lanh"]}),
        ("studio gần Duy Tân 1km", {"room_types": ["studio"], "school_id": 4, "max_distance_km": 1.0}),
    ],
)
def test_parse_rule(q, expect):
    f = parse_rule(q, SCHOOLS).model_dump()
    for k, v in expect.items():
        assert f[k] == v, (k, f[k])


def test_reconcile_fixes_small_llm_mistakes():
    from app.query_parser import SearchFilters, reconcile

    q = "phòng dưới 2tr5 gần bách khoa có gác"
    llm = SearchFilters(budget_max=2500, districts=list(seed.DISTRICT_WEIGHTS), amenities=["gac_lung", "may_lanh", "wifi"], keywords=q)
    f = reconcile(llm, parse_rule(q, SCHOOLS), q)
    assert f.budget_max == 2_500_000 and f.districts == [] and f.amenities == ["gac_lung"] and f.keywords is None


def test_extract_rule():
    ex = extract_rule("Cho thuê phòng kiệt 45 Ngô Sĩ Liên, 22m2 có gác, máy lạnh, wc riêng. Giá 2tr2, điện 3k5, nước 100k/người, cọc 1 tháng")
    assert ex.price == 2_200_000 and ex.area == 22 and ex.district == "Liên Chiểu"
    assert ex.electricity_price == 3500 and ex.water_price == 100_000 and ex.deposit_months == 1
    assert {"gac_lung", "may_lanh", "wc_rieng"} <= set(ex.amenities)


def test_extract_rule_ignores_large_amount_before_nguoi_as_occupancy():
    ex = extract_rule("Cho thuê phòng tại Hải Châu, Đà Nẵng, giá 3 triệu. Nội dung có cụm 7000 người.")
    assert ex.max_people is None


def test_search_and_risk(client):
    r = client.post("/api/search", json={"query": "phòng dưới 2tr5 gần Bách khoa có gác"}).json()
    assert r["total"] > 0
    assert all(i["price"] <= 2_500_000 and i["risk_level"] != "high" for i in r["items"])
    scam = client.get("/api/admin/moderation", headers=token(client, "admin@phongoi.vn", "Admin@2026")).json()["items"][0]
    assert scam["risk_score"] >= 65


def test_roles(client):
    assert client.get("/api/admin/overview").status_code == 401
    st = token(client, "sinhvien@phongoi.vn", "Sinhvien@2026")
    assert client.get("/api/admin/overview", headers=st).status_code == 403
    assert client.get("/api/recommendations", headers=st).json()["top_pick"] is not None


def test_sample_fixture_ingest_dedupes_without_exposing_demo_source(client):
    at = token(client, "admin@phongoi.vn", "Admin@2026")
    db = SessionLocal()
    source = CrawlSource(name="Test fixture only", kind="sample", spider=None, start_url="crawler/fixtures/sample_posts.json",
                         enabled=False, status="paused", connector_type="first_party", integration_status="ready")
    db.add(source)
    db.commit()
    source_id = source.id
    db.close()
    try:
        res = client.post(f"/api/admin/sources/{source_id}/run", headers=at).json()["result"]
        # 10 tin mẫu: có 1 tin thiếu giá bị loại, các tin trùng (với nhau hoặc với dữ liệu sẵn có) được gộp.
        assert res["new"] >= 4 and res["dup"] >= 1 and res["new"] + res["dup"] + res["errors"] == 10
    finally:
        db = SessionLocal()
        db.query(CrawlRun).filter_by(source_id=source_id).delete()
        db.query(CrawlSource).filter_by(id=source_id).delete()
        db.commit()
        db.close()


def test_password_reset_and_change(client):
    email = "quenmk@example.com"
    client.post("/api/auth/register", json={"full_name": "Thử Quên", "email": email, "password": "Matkhau@1"})
    assert "dev_reset_url" not in client.post("/api/auth/forgot", json={"email": "khongco@example.com"}).json()
    url = client.post("/api/auth/forgot", json={"email": email}).json()["dev_reset_url"]
    tok = url.split("token=")[1]
    assert client.post("/api/auth/reset", json={"token": tok, "password": "Matkhau@2"}).status_code == 200
    assert client.post("/api/auth/reset", json={"token": tok, "password": "Matkhau@3"}).status_code == 400  # dùng một lần
    h = token(client, email, "Matkhau@2")
    assert client.put("/api/me/password", headers=h, json={"current_password": "sai", "new_password": "Matkhau@4"}).status_code == 400
    assert client.put("/api/me/password", headers=h, json={"current_password": "Matkhau@2", "new_password": "Matkhau@4"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": email, "password": "Matkhau@4"}).status_code == 200


def test_notifications_and_prefs(client):
    st = token(client, "sinhvien@phongoi.vn", "Sinhvien@2026")
    at = token(client, "admin@phongoi.vn", "Admin@2026")
    assert client.put("/api/me/notification-prefs", headers=st, json={"weekly": True, "hack": True}).json()["weekly"] is True
    before = client.get("/api/me/notifications/unread", headers=at).json()["count"]
    lid = client.post("/api/search", json={"query": "phòng Liên Chiểu"}).json()["items"][0]["id"]
    client.post(f"/api/listings/{lid}/report", headers=st, json={"reason": "wrong_info", "description": "Ảnh khác thực tế"})
    assert client.get("/api/me/notifications/unread", headers=at).json()["count"] == before + 1
    n = client.get("/api/me/notifications", headers=at).json()[0]
    assert n["link"] == "/admin/kiem-duyet"
    client.post("/api/me/notifications/read", headers=at, json={"id": n["id"]})
    assert client.get("/api/me/notifications/unread", headers=at).json()["count"] == before


def test_admin_sources_require_terms(client):
    at = token(client, "admin@phongoi.vn", "Admin@2026")
    s = client.post("/api/admin/sources", headers=at, json={"name": "Nguồn thử", "start_url": "https://example.com/phong-tro"}).json()
    assert s["enabled"] is False and s["status"] == "paused"
    assert client.patch(f"/api/admin/sources/{s['id']}", headers=at, json={"enabled": True}).status_code == 422
    assert client.post(f"/api/admin/sources/{s['id']}/run", headers=at).status_code == 422
    still_blocked = client.patch(f"/api/admin/sources/{s['id']}", headers=at,
                                 json={"enabled": True, "config": {"item_selector": ".item", "terms_checked": True}})
    assert still_blocked.status_code == 422
    configured = client.patch(f"/api/admin/sources/{s['id']}", headers=at,
                              json={"config": {"item_selector": ".item", "terms_checked": True}})
    assert configured.status_code == 200 and configured.json()["enabled"] is False
    approval = client.post(f"/api/admin/sources/{s['id']}/approve", headers=at, json={
        "terms_url": "https://example.com/terms",
        "robots_url": "https://example.com/robots.txt",
        "notes": "Đã kiểm tra quyền thu thập và giới hạn truy cập.",
    })
    assert approval.status_code == 200
    assert approval.json()["integration_status"] == "ready"
    assert approval.json()["approved_at"]
    ok = client.patch(f"/api/admin/sources/{s['id']}", headers=at, json={"enabled": True})
    assert ok.status_code == 200 and ok.json()["enabled"] is True
    assert client.delete(f"/api/admin/sources/{s['id']}", headers=at).json()["deleted"] is True


def test_admin_catalog_extends_parsers(client):
    from app.catalog import find_amenities

    at = token(client, "admin@phongoi.vn", "Admin@2026")
    key = client.post("/api/admin/catalog/amenities", headers=at, json={"label": "Thang máy", "synonyms": ["có thang máy", "elevator"]}).json()["key"]
    assert key in find_amenities("phòng mới có thang máy, gần biển")
    client.put("/api/admin/catalog/amenities/wifi", headers=at, json={"synonyms": ["wifi", "mạng cáp quang"]})
    assert "wifi" in find_amenities("có mạng cáp quang tốc độ cao")
    client.post("/api/admin/catalog/scam-keywords", headers=at, json={"keyword": "đặt cọc qua zalo"})
    cat = client.get("/api/admin/catalog", headers=at).json()
    assert any(k["keyword"] == "đặt cọc qua zalo" and k["custom"] for k in cat["scam_keywords"])
    assert client.delete("/api/admin/catalog/amenities/wifi", headers=at).status_code == 400
    assert client.delete(f"/api/admin/catalog/amenities/{key}", headers=at).json()["deleted"] is True
    assert key not in find_amenities("có thang máy")


def test_landlord_edit_room(client):
    lt = token(client, "chutro@phongoi.vn", "Chutro@2026")
    room = next(r for r in client.get("/api/landlord/rooms", headers=lt).json()["items"] if r["status"] == "active")
    d = client.get(f"/api/landlord/rooms/{room['id']}", headers=lt).json()
    assert d["address"] and "amenities" in d
    out = client.patch(f"/api/landlord/rooms/{room['id']}", headers=lt,
                       json={"price": d["price"] - 100_000, "amenities": [*d["amenities"], "khong_ton_tai"], "area": 25}).json()
    assert out["price"] == d["price"] - 100_000 and "khong_ton_tai" not in out.get("amenities", [])
    other = token(client, "sinhvien@phongoi.vn", "Sinhvien@2026")
    assert client.get(f"/api/landlord/rooms/{room['id']}", headers=other).status_code == 403


