from types import SimpleNamespace

from app import worker
from app.source_connectors import apply_run_health, is_helprent_student_housing, normalize_helprent, rate_limit_delay


def test_helprent_listing_is_normalized_for_the_shared_pipeline():
    raw = normalize_helprent(
        {
            "slug": "studio-son-tra-1",
            "type_label": "Studio",
            "bedrooms": 1,
            "price_month": 4_500_000,
            "district": "Son Tra",
            "furnished": True,
            "url": "https://helprentdanang.com/danang/rentals/studio/studio-son-tra-1/",
            "source": "Owner",
        },
        "HelpRent Da Nang API",
    )
    assert raw.url == "https://helprentdanang.com/danang/rentals/studio/studio-son-tra-1/"
    assert raw.source_name == "HelpRent Da Nang API"
    assert "4.500.000" in raw.text and "Sơn Trà" in raw.text and "đầy đủ nội thất" in raw.text


def test_rate_limit_text_controls_real_download_delay():
    assert rate_limit_delay("1 yêu cầu / 2 giây") == 2.0
    assert rate_limit_delay("10 yêu cầu / phút") == 6.0
    assert rate_limit_delay("invalid") == 2.0


def test_helprent_connector_filters_out_of_scope_or_missing_price_listings():
    assert is_helprent_student_housing({"type": "room", "price_month": 4_500_000})
    assert is_helprent_student_housing({"type": "apartment", "price_month": 12_000_000})
    assert not is_helprent_student_housing({"type": "house", "price_month": 8_000_000})
    assert not is_helprent_student_housing({"type": "studio", "price_month": 0})
    assert not is_helprent_student_housing({"type": "apartment", "price_month": 35_000_000})


def test_three_consecutive_failures_auto_pause_source():
    source = SimpleNamespace(health_score=100, consecutive_failures=2, enabled=True, status="ok", last_health_at=None)
    apply_run_health(source, "error")
    assert source.health_score == 0
    assert source.consecutive_failures == 3
    assert source.enabled is False and source.status == "paused"


def test_success_recovers_health_without_auto_enabling_source():
    source = SimpleNamespace(health_score=0, consecutive_failures=2, enabled=False, status="paused", last_health_at=None)
    apply_run_health(source, "success")
    assert source.health_score == 100 and source.consecutive_failures == 0
    assert source.enabled is False and source.status == "paused"


def test_worker_treats_scrapy_downloader_exceptions_as_failed_process():
    output = "scrapy stats: {'downloader/exception_count': 2, 'finish_reason': 'finished'}"
    assert worker.scrapy_run_failed(0, output) is True


def test_worker_treats_scrapy_pipeline_item_errors_as_failed_process():
    output = "scrapy stats: {'item_error_count': 15, 'finish_reason': 'finished'}"
    assert worker.scrapy_run_failed(0, output) is True


def test_worker_accepts_clean_scrapy_process_output():
    output = "scrapy stats: {'downloader/response_count': 2, 'finish_reason': 'finished'}"
    assert worker.scrapy_run_failed(0, output) is False


def test_external_crawl_with_no_items_is_partial_not_success():
    assert worker.completed_run_status(error_count=0, collected=0, expects_items=True) == "partial"
    assert worker.completed_run_status(error_count=0, collected=0, expects_items=False) == "success"


def test_worker_decodes_scrapy_output_as_utf8_with_replacement(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    worker.run_scrapy_process(["scrapy"], {})
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"


def test_helprent_detail_image_extraction_and_duplicate_image_merge():
    from app.source_connectors import extract_helprent_detail_meta

    sample_html = """
    <html><head>
      <meta property="og:image" content="https://helprentdanang.com/photo/444144/">
      <script type="application/ld+json">
      {"@context": "https://schema.org", "@type": "Apartment", "name": "Studio Phan Huy Ích, Sơn Trà",
       "description": "Studio rộng 28m2 đường Phan Huy Ích, Sơn Trà, gần biển Mỹ Khê, có ban công.",
       "floorSize": {"@type": "QuantitativeValue", "value": 28, "unitCode": "MTK"},
       "image": ["https://helprentdanang.com/photo/444144/", "https://helprentdanang.com/photo/444145/"]}
      </script>
      <script type="application/json" id="lp-all-photos">
      ["https://helprentdanang.com/photo/444144/", "https://helprentdanang.com/photo/444145/", "https://helprentdanang.com/photo/444146/"]
      </script>
    </head></html>
    """
    meta = extract_helprent_detail_meta(sample_html)
    assert len(meta["images"]) == 3
    assert meta["images"][0] == "https://helprentdanang.com/photo/444144/"
    assert meta["area"] == 28.0
    assert "Phan Huy Ích" in meta["description"]

    raw = normalize_helprent(
        {
            "slug": "studio-son-tra-1",
            "type_label": "Studio",
            "bedrooms": 1,
            "price_month": 4_500_000,
            "district": "Son Tra",
            "furnished": True,
            "url": "https://helprentdanang.com/danang/rentals/studio/studio-son-tra-1/",
            "source": "Owner",
            "images": meta["images"],
            "area": meta["area"],
            "description": meta["description"],
        },
        "HelpRent Da Nang API",
    )
    assert len(raw.images) == 3
    assert "28m2" in raw.text

