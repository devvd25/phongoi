"""TDD tests for Hybrid AI (CPU ML Classifier + Multi-key Cloud LLM) and 24/7 Facebook Group Bot."""

from app.db import SessionLocal
from app.extract import extract_rule
from app.fb_group_bot import (
    clean_facebook_url,
    ensure_chronological_group_url,
    generate_content_fingerprint,
    generate_post_id,
    is_checkpoint_or_login_wall,
    parse_graphql_feed_payload,
    sanitize_cookie_payload,
)
from app.llm import KeyRotator, active_ai_label
from app.ml_classifier import classify_post
from app.pipeline import RawPost, process_raw


def test_ml_post_classifier_distinguishes_offer_seeker_and_spam():
    offer = classify_post(
        "Cho thuê phòng trọ mới xây kiệt Hoàng Diệu, Hải Châu, Đà Nẵng. "
        "Giá 2tr8/tháng, diện tích 25m2, có gác lửng, máy lạnh, wc riêng, giờ giấc tự do. Lh chính chủ 0905123456."
    )
    assert offer["intent"] == "rental_offer"
    assert offer["is_rental"] is True
    assert offer["poster_type"] == "owner"
    assert offer["is_broker"] is False

    seeker = classify_post(
        "Mình là nữ sinh viên năm 2 ĐH Kinh Tế Đà Nẵng cần tìm phòng trọ hoặc tìm người ở ghép "
        "khu vực Ngũ Hành Sơn, Sơn Trà tài chính dưới 2tr5, có máy lạnh. Ai có phòng trống chỉ giúp em với ạ!"
    )
    assert seeker["intent"] == "room_seeker"
    assert seeker["is_rental"] is False

    spam = classify_post(
        "Dịch vụ xe tải chuyển nhà, chuyển phòng trọ sinh viên giá rẻ toàn Đà Nẵng. "
        "Nhận lắp đặt wifi Viettel FPT tận nơi, chấm bài ib ngay."
    )
    assert spam["intent"] == "spam"
    assert spam["is_rental"] is False

    broker = classify_post(
        "Hệ thống căn hộ mini & studio cho thuê khắp Hải Châu, Sơn Trà, Ngũ Hành Sơn. "
        "Nhiều mức giá chỉ từ 3tr - 6tr/tháng, giỏ hàng hơn 50 phòng trống, hỗ trợ tìm phòng miễn phí, inbox gửi video thực tế."
    )
    assert broker["intent"] == "rental_offer"
    assert broker["is_rental"] is True
    assert broker["poster_type"] == "broker"
    assert broker["is_broker"] is True


def test_danang_shorthand_extraction_and_whitelist():
    ex = extract_rule("ptr 2tr5 hc wifi ml kcc gtd vsr 22m2")
    assert ex.price == 2_500_000
    assert ex.district == "Hải Châu"
    assert ex.area == 22.0
    assert "wifi" in ex.amenities
    assert "may_lanh" in ex.amenities
    assert "gio_tu_do" in ex.amenities
    assert "wc_rieng" in ex.amenities


def test_pipeline_rejects_room_seeker_posts_via_ml_classifier():
    db = SessionLocal()
    try:
        raw = RawPost(
            source_name="FB Group · Hội Phòng Trọ Đà Nẵng",
            url="https://www.facebook.com/groups/phongtrodanang/posts/999888777/",
            text=(
                "Em là tân sinh viên ĐH Bách Khoa Đà Nẵng cần tìm phòng trọ khu vực Hòa Khánh, Liên Chiểu "
                "tài chính khoảng 2 triệu/tháng, có gác lửng và wifi. Anh chị nào biết chỉ giúp em với ạ!"
            ),
        )
        res = process_raw(db, raw)
        assert res["status"] == "rejected"
        assert res["stage"] == "clean"
        assert "tìm phòng" in res.get("reason", "").lower() or "spam" in res.get("reason", "").lower()
    finally:
        db.close()


def test_multi_key_rotation_and_cooldown_in_llm():
    rotator = KeyRotator("key_1, key_2, key_3")
    assert len(rotator.keys) == 3

    k1 = rotator.next_key()
    k2 = rotator.next_key()
    k3 = rotator.next_key()
    assert {k1, k2, k3} == {"key_1", "key_2", "key_3"}

    # Mark key_1 and key_2 as rate-limited -> must pick key_3
    rotator.mark_rate_limited("key_1", cooldown_sec=60)
    rotator.mark_rate_limited("key_2", cooldown_sec=60)
    assert rotator.next_key() == "key_3"

    # Active AI label never requires local GPU Ollama
    label = active_ai_label()
    assert "ML CPU" in label


def test_fb_group_bot_url_normalization_and_chronological_enforcement():
    url = ensure_chronological_group_url("https://www.facebook.com/groups/phongtrodanang")
    assert url == "https://www.facebook.com/groups/phongtrodanang?sorting_setting=CHRONOLOGICAL"

    clean1 = clean_facebook_url(
        "https://www.facebook.com/groups/phongtrodanang/posts/123456789/?__cft__[0]=AZX&__tn__=%2CO&ref=share"
    )
    assert clean1 == "https://www.facebook.com/groups/phongtrodanang/posts/123456789/"

    clean2 = clean_facebook_url("https://www.facebook.com/photo/?fbid=111&set=pcb.987654321")
    assert clean2 == "https://www.facebook.com/posts/987654321/"


def test_fb_group_bot_cookie_sanitizer_and_dual_deduplication():
    raw_cookie_editor = [
        {"name": "c_user", "value": "100012345", "domain": "facebook.com", "sameSite": "no_restriction", "secure": True},
        {"name": "xs", "value": "secret_xs", "domain": ".facebook.com", "sameSite": "strict", "httpOnly": True},
    ]
    state = sanitize_cookie_payload(raw_cookie_editor)
    assert isinstance(state, dict)
    assert len(state["cookies"]) == 2
    assert state["cookies"][0]["sameSite"] == "None"
    assert state["cookies"][0]["domain"] == ".facebook.com"
    assert state["cookies"][1]["sameSite"] == "Strict"

    pid = generate_post_id("https://www.facebook.com/groups/123/posts/456789/", "grp1", "Nguyen A", "Cho thue phong")
    assert pid == "fb_post_456789"

    fp1 = generate_content_fingerprint("Nguyen Van A", "Cho thuê phòng trọ 2tr5 Hải Châu Đà Nẵng mới 100%   ")
    fp2 = generate_content_fingerprint("nguyen van a", "cho thue phong tro 2tr5 hai chau da nang moi 100%")
    assert fp1 == fp2
    assert fp1.startswith("fp_")

    assert is_checkpoint_or_login_wall("https://www.facebook.com/checkpoint/1501092823525282/", "Facebook", "") is True
    assert is_checkpoint_or_login_wall("https://www.facebook.com/groups/123", "Nhóm Trọ", "Tài khoản của bạn đã bị khóa") is True
    assert is_checkpoint_or_login_wall("https://www.facebook.com/groups/123", "Hội Phòng Trọ Đà Nẵng", "Cho thuê phòng 2tr5") is False


def test_fb_group_bot_graphql_post_extraction_with_photos():
    sample_graphql = """for (;;);
{"data":{"node":{"group_feed":{"edges":[{"node":{"post_id":"888999111","creation_time":1794200000,"actors":[{"name":"Chủ Trọ Hải Châu"}],"message":{"text":"Cho thuê phòng trọ đường Nguyễn Văn Linh, Hải Châu, Đà Nẵng. Giá 2.6 triệu/tháng, rộng 24m2, full nội thất."},"attachments":[{"styles":{"attachment":{"all_subattachments":{"nodes":[{"media":{"image":{"uri":"https://scontent.fdad1-1.fna.fbcdn.net/v/t39.30808-6/room1_full.jpg?_nc_cat=101"}}},{"media":{"image":{"uri":"https://scontent.fdad1-1.fna.fbcdn.net/v/t39.30808-6/room2_full.jpg?_nc_cat=102"}}}]}}}}]}}]}}}}
"""
    posts = parse_graphql_feed_payload(sample_graphql, group_url="https://www.facebook.com/groups/phongtrodanang")
    assert len(posts) == 1
    p = posts[0]
    assert p["post_id"] == "fb_post_888999111"
    assert "Nguyễn Văn Linh" in p["text"]
    assert len(p["images"]) == 2
    assert "room1_full.jpg" in p["images"][0]


def test_worker_crawl_source_executes_fb_group_bot_and_filters_seeker_spam():
    from app.models import CrawlRun, CrawlSource
    from app.worker import crawl_source

    db = SessionLocal()
    created_temp = False
    try:
        src = db.query(CrawlSource).filter_by(profile_id="fb-group-danang-02").first()
        if not src:
            src = CrawlSource(
                name="AI Bot · FB Group Đà Nẵng #02 (trodanang)",
                kind="playwright",
                spider="generic",
                profile_id="fb-group-danang-02",
                connector_type="html_playwright",
                integration_status="ready",
                start_url="http://web.facebook.com/groups/trodanang/",
                enabled=False,
                status="paused",
                config={"item_selector": "[role='feed'] > div", "terms_checked": False},
            )
            db.add(src)
            db.commit()
            db.refresh(src)
            created_temp = True
        source_id = src.id
    finally:
        db.close()

    try:
        res = crawl_source(source_id)
        assert res["status"] == "success"
        assert res["errors"] == 0
        assert (res["new"] + res["dup"]) == 6
    finally:
        db = SessionLocal()
        s = db.get(CrawlSource, source_id)
        if s:
            if created_temp:
                db.query(CrawlRun).filter_by(source_id=source_id).delete()
                db.delete(s)
            else:
                s.enabled = False
                s.status = "paused"
        db.commit()
        db.close()


def test_sources_api_separates_website_and_fb_group_sources():
    from app.models import CrawlSource
    from app.routes_admin import source_out
    from app.source_profiles import profiles as get_profiles

    fb_src = CrawlSource(
        id=901,
        name="AI Bot · FB Group Đà Nẵng #02 (trodanang)",
        kind="playwright",
        profile_id="fb-group-danang-02",
        connector_type="html_playwright",
        integration_status="ready",
        start_url="http://web.facebook.com/groups/trodanang/",
        enabled=True,
        status="ok",
    )
    web_src = CrawlSource(
        id=902,
        name="Phongtro123 Đà Nẵng",
        kind="scrapy",
        profile_id="phongtro123",
        connector_type="html_static",
        integration_status="ready",
        start_url="https://phongtro123.com/tinh-thanh/da-nang",
        enabled=True,
        status="ok",
    )
    assert source_out(fb_src, None)["source_group"] == "fb_group"
    assert source_out(web_src, None)["source_group"] == "website"

    all_profiles = get_profiles()
    fb_profiles = [p for p in all_profiles if p["id"].startswith("fb-group-danang-")]
    assert len(fb_profiles) == 38
    retired_fake_fb = {
        "facebook-groups",
        "fb-group-phongtro-danang-247",
        "fb-group-nhatro-sv-danang",
        "fb-group-canho-studio-danang",
        "fb-group-nha-nguyen-can-danang",
        "fb-group-phongtro-haichau-sontra",
    }
    assert retired_fake_fb.isdisjoint({p["id"] for p in all_profiles})


def test_fb_cookie_parser_supports_both_json_and_raw_header_string():
    from app.fb_group_bot import parse_flexible_cookie_input

    # 1. Raw cookie string (c_user=...; xs=...)
    state1, meta1 = parse_flexible_cookie_input("datr=xyz; c_user=1000555666777; xs=42%3Asecret_xs_val; fr=0abc")
    assert meta1["connected"] is True
    assert meta1["c_user"] == "1000555666777"
    assert meta1["cookie_count"] == 4
    assert any(c["name"] == "c_user" and c["value"] == "1000555666777" for c in state1["cookies"])

    # 2. Cookie-Editor JSON string
    json_input = '[{"name": "c_user", "value": "1000999888", "domain": "facebook.com", "sameSite": "no_restriction"}, {"name": "xs", "value": "xs_token", "domain": ".facebook.com"}]'
    state2, meta2 = parse_flexible_cookie_input(json_input)
    assert meta2["connected"] is True
    assert meta2["c_user"] == "1000999888"
    assert len(state2["cookies"]) == 2


def test_multi_cookie_proxy_pool_and_live_checker(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    from app.config import settings
    from app.fb_group_bot import (
        check_fb_account_live,
        delete_fb_account,
        get_fb_cookie_status,
        normalize_proxy_config,
        save_fb_cookie,
        select_next_fb_account,
    )

    pool_file = tmp_path / "fb-accounts.json"
    monkeypatch.setattr(settings, "fb_storage_state_path", str(pool_file))

    # 1. Proxy normalization supports ip:port:user:pass and standard URLs
    pw_proxy, httpx_proxy, display_proxy = normalize_proxy_config("103.45.67.89:8080:myuser:mypass")
    assert pw_proxy == {"server": "http://103.45.67.89:8080", "username": "myuser", "password": "mypass"}
    assert httpx_proxy == "http://myuser:mypass@103.45.67.89:8080"
    assert "103.45.67.89:8080" in display_proxy

    # 2. Add 2 accounts with different proxies (without network call during unit save)
    save_fb_cookie(
        "c_user=1000111111; xs=secret_1; datr=d1",
        label="Clone Đà Nẵng 1",
        proxy_url="103.11.22.33:8000:u1:p1",
        check_live=False,
    )
    save_fb_cookie(
        "c_user=1000222222; xs=secret_2; datr=d2",
        label="Clone Đà Nẵng 2",
        proxy_url="http://u2:p2@103.44.55.66:9000",
        check_live=False,
    )

    status = get_fb_cookie_status()
    assert status["connected"] is True
    assert status["total_accounts"] == 2
    assert len(status["accounts"]) == 2

    # 3. Least-used account rotation across crawls
    acc1 = select_next_fb_account()
    acc2 = select_next_fb_account()
    assert {acc1["c_user"], acc2["c_user"]} == {"1000111111", "1000222222"}

    # 4. Live check simulation (LIVE vs EXPIRED)
    mock_resp_live = MagicMock()
    mock_resp_live.status_code = 200
    mock_resp_live.url = "https://mbasic.facebook.com/profile.php?id=1000111111"
    mock_resp_live.text = '<html><title>Nguyễn Văn A</title><a href="/logout.php">Đăng xuất</a></html>'
    mock_resp_live.headers = {}

    with monkeypatch.context() as m:
        m.setattr("app.fb_group_bot._request_fb_profile_check", lambda acc: mock_resp_live)
        checked = check_fb_account_live("acc_1000111111")
        acc_info = next(a for a in checked["accounts"] if a["c_user"] == "1000111111")
        assert acc_info["live_status"] == "live"

    mock_resp_die = MagicMock()
    mock_resp_die.status_code = 200
    mock_resp_die.url = "https://mbasic.facebook.com/login.php?next=..."
    mock_resp_die.text = '<html><form id="login_form">Đăng nhập Facebook</form></html>'
    mock_resp_die.headers = {}

    with monkeypatch.context() as m:
        m.setattr("app.fb_group_bot._request_fb_profile_check", lambda acc: mock_resp_die)
        checked = check_fb_account_live("acc_1000222222")
        acc_info2 = next(a for a in checked["accounts"] if a["c_user"] == "1000222222")
        assert acc_info2["live_status"] == "expired"

    # Rotation now only picks the LIVE account (1000111111) and skips the EXPIRED account (1000222222)!
    next_acc = select_next_fb_account()
    assert next_acc["c_user"] == "1000111111"

    # Delete account 2
    after_del = delete_fb_account("acc_1000222222")
    assert after_del["total_accounts"] == 1


def test_broker_listing_ai_summary_is_always_list_and_price_estimate_positive():
    from app.models import Listing
    from app.pricing import estimate
    from app.routes_public import listing_detail

    db = SessionLocal()
    created_id = None
    try:
        # 1. Legacy listing 270 or simulated legacy string ai_summary must be normalized to list[str]
        raw = RawPost(
            source_name="ThuêPhòngTrọ.com · Đà Nẵng",
            url="https://thuephongtro.com/test-broker-summary-list-999111.html",
            text=(
                "Hệ thống căn hộ mini & phòng trọ cho thuê tại đường Hoàng Văn Thái, Liên Chiểu, Đà Nẵng. "
                "Giá 2tr4/tháng, diện tích 23m2, có gác lửng, máy lạnh, giỏ hàng hơn 20 phòng trống, inbox gửi video."
            ),
        )
        res = process_raw(db, raw)
        assert res["status"] in ("new", "duplicate")
        created_id = res["listing_id"]
        listing = db.get(Listing, created_id)
        assert isinstance(listing.ai_summary, list), f"Expected list, got {type(listing.ai_summary)}: {listing.ai_summary}"
        assert all(isinstance(item, str) for item in listing.ai_summary)

        # Simulate legacy corrupted string in DB like listing 270
        listing.ai_summary = "['Có gác lửng'] · Nguồn đăng: Môi giới / Hệ thống"
        db.commit()

        detail = listing_detail(created_id, db=db, user=None)
        assert isinstance(detail["ai_summary"], list)
        assert "Có gác lửng" in detail["ai_summary"]
        assert any("Nguồn đăng: Môi giới / Hệ thống" in s for s in detail["ai_summary"])

        # 2. Price estimate for Liên Chiểu 23m2 o_ghep must be positive
        est = estimate(db, "Liên Chiểu", 23.0, ["gac_lung"], "o_ghep")
        assert est["mid"] >= 500_000
        assert est["low"] >= 400_000
        assert est["high"] >= est["mid"]
    finally:
        if created_id:
            obj = db.get(Listing, created_id)
            if obj:
                db.delete(obj)
                db.commit()
        db.close()


def test_upgraded_ai_insights_and_xai_price_valuation():
    from app.routes_public import listing_detail

    db = SessionLocal()
    try:
        detail = listing_detail(180, db=db, user=None)
        # 1. Check ai_insights structure
        assert "ai_insights" in detail
        insights = detail["ai_insights"]
        assert insights["poster_type"] in ("owner", "broker")
        assert 50 <= insights["poster_confidence"] <= 100
        assert isinstance(insights["pros"], list) and len(insights["pros"]) >= 2
        assert isinstance(insights["caveats"], list) and len(insights["caveats"]) >= 1
        assert isinstance(insights["suitability"], str) and len(insights["suitability"]) > 15

        # 2. Check XAI price_analysis structure
        pa = detail["price_analysis"]
        assert "segment_label" in pa
        assert "sample_count" in pa
        assert "factors" in pa and isinstance(pa["factors"], list) and len(pa["factors"]) >= 3
        assert pa["factors"][0]["kind"] == "base"
        assert "verdict" in pa and "label" in pa["verdict"]
        assert "model_meta" in pa["estimate"]
    finally:
        db.close()







