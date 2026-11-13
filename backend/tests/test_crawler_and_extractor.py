import sys
from pathlib import Path
import pytest

CRAWLER_DIR = str(Path(__file__).resolve().parents[2] / "crawler")
if CRAWLER_DIR not in sys.path:
    sys.path.insert(0, CRAWLER_DIR)

from app.extract import extract, _price
from parsel import Selector
from phongoi_crawler.spiders.generic_listing import extract_clean_images

def test_price_extraction_usd():
    """Nhận diện giá thuê theo USD và quy đổi sang VND."""
    text1 = "Available $445 USD - Apartment in Son Tra Da Nang"
    p1 = _price(text1.lower())
    assert p1 is not None
    assert 11_000_000 <= p1 <= 12_000_000

    text2 = "Cho thuê căn hộ giá $500 / tháng tại Hải Châu"
    p2 = _price(text2.lower())
    assert p2 is not None
    assert 12_000_000 <= p2 <= 13_000_000

def test_price_extraction_shorthand():
    """Nhận diện các kiểu viết tắt giá phổ biến không có chữ tháng."""
    assert _price("cho thuê phòng 2500k khép kín") == 2_500_000
    assert _price("phòng trọ giá 1800k") == 1_800_000
    assert _price("phòng 3tr5 full nội thất") == 3_500_000
    assert _price("giá 2.8tr gần đại học") == 2_800_000

def test_image_extraction_lazy_load_and_filter():
    """Trích xuất ảnh ưu tiên data-src và lọc bỏ icon/logo/placeholder."""
    html = """
    <html>
      <body>
        <article class="post">
          <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" 
               data-src="https://example.com/photos/room-main.jpg" alt="Phòng chính" />
          <img src="/static/images/logo.png" alt="Logo website" />
          <img data-original="https://example.com/photos/room-wc.jpg" src="/assets/placeholder.jpg" />
          <img src="/images/icon-bed.svg" />
          <img src="https://example.com/photos/room-balcony.jpg" />
        </article>
      </body>
    </html>
    """
    sel = Selector(text=html)
    class MockResponse:
        url = "https://example.com/post-123"
        def css(self, query):
            return sel.css(query)
        def urljoin(self, path):
            if path.startswith("http"):
                return path
            return f"https://example.com{path}"

    imgs = extract_clean_images(MockResponse(), "article.post")
    assert "https://example.com/photos/room-main.jpg" in imgs
    assert "https://example.com/photos/room-wc.jpg" in imgs
    assert "https://example.com/photos/room-balcony.jpg" in imgs
    assert not any("base64" in u or "logo" in u or "icon" in u or "svg" in u for u in imgs)


def test_overview_pipeline_synchronized_with_kpis():
    """Luồng xử lý dữ liệu trên trang tổng quan phải đồng bộ với số liệu KPI 24h."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import SessionLocal, utcnow
    from app.models import CrawlRun, CrawlSource

    client = TestClient(app)
    auth = client.post("/api/auth/login", json={"email": "admin@phongoi.vn", "password": "Admin@2026"}).json()
    token = auth.get("token")
    assert token is not None

    db = SessionLocal()
    src = db.query(CrawlSource).first()
    # Tạo 1 CrawlRun giả lập có 10 tin mới, 5 tin trùng
    run = CrawlRun(source_id=src.id, started_at=utcnow(), new_count=10, dup_count=5, error_count=0, status="success")
    db.add(run)
    db.commit()
    db.close()

    res = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    kpis = data["kpis"]
    pipeline = data["pipeline"]

    assert pipeline is not None
    # Số tin ở giai đoạn collect phải khớp với collected_24h
    collect_stage = next(s for s in pipeline["stages"] if s["key"] == "collect")
    assert collect_stage["count"] == kpis["collected_24h"]
    assert collect_stage["count"] >= 15


def test_title_extraction_ignores_json_script():
    """Trích xuất tiêu đề không bị dính chuỗi JSON-LD schema hoặc code."""
    text_with_json = '{"@context":"https://schema.org","@type":"Product"} FPT Plaza 2-Bedroom 61m² tại Ngũ Hành Sơn. Giá 6.8tr full nội thất.'
    ex = extract(text_with_json)
    assert not ex.title.startswith("{")
    assert not ex.title.startswith("@")
    assert "FPT Plaza" in ex.title


def test_image_filter_strips_facebook_pixel_and_placeholders():
    """Lọc bỏ Facebook Pixel tracking, ảnh bản đồ tĩnh và ảnh mặc định ở cả spider và serializer."""
    from app.serializers import clean_listing_images

    html = """
    <html><body>
      <img src="https://www.facebook.com/tr?id=903223921926904&ev=PageView&noscript=1" />
      <img src="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20246%20162'%3E%3C/svg%3E" />
      <img src="https://bds123.vn/images/openmap.png" />
      <img src="https://thuephongtro.com/images/default.jpg" />
      <img src="https://img.meeyland.com/meeyland-ai/images/2026/11/room1.jpg" />
    </body></html>
    """
    sel = Selector(text=html)

    class MockResponse:
        url = "https://meeyland.com/post-180"

        def css(self, query):
            return sel.css(query)

        def urljoin(self, path):
            return path

    imgs = extract_clean_images(MockResponse())
    assert imgs == ["https://img.meeyland.com/meeyland-ai/images/2026/11/room1.jpg"]

    cleaned = clean_listing_images([
        "https://www.facebook.com/tr?id=903223921926904&ev=PageView&noscript=1",
        "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E",
        "https://bds123.vn/images/openmap.png",
        "https://thuephongtro.com/images/default.jpg",
        "https://img.meeyland.com/meeyland-ai/images/2026/11/room1.jpg",
    ])
    assert cleaned == ["https://img.meeyland.com/meeyland-ai/images/2026/11/room1.jpg"]

