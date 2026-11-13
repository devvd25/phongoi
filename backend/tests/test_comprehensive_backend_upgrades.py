"""TDD test suite cho 6 Module nâng cấp Backend & AI (Phòng Ơi)."""

from app.catalog import find_amenities, find_room_types
from app.db import SessionLocal
from app.extract import extract_rule
from app.geo import approx_location, haversine_km
from app.models import Listing, ListingSource, School
from app.pricing import monthly_cost
from app.query_parser import parse_rule
from app.risk import assess, quality
from app.routes_public import deduplicate_sources, rank_similar_listings


def test_module1_location_extraction_strips_footer_and_matches_exact_street_district():
    # 1. Bài 180: Mẹ Nhu (Thanh Khê) kèm nhiễu Meeyland
    raw_180 = (
        "Trọ sleep box - mẹ nhu - điều hoà 24/14 - bao điện nước. "
        "Cho thuê phòng trọ Đ. Mẹ Nhu, P. Thanh Khê, Tp. Đà Nẵng | 307898289 | Meeyland "
        "Mua bán nhà đất Bán căn hộ chung cư Đăng nhập / Đăng ký Đăng tin "
        "Mô tả: Chỉ 1,9 triệu/tháng – bao điện nước, Điều hòa, Tủ lạnh, Máy nước nóng, Bếp từ + lò vi sóng, Máy giặt, Wifi. "
        "Phản ánh tin đăng Cho thuê phòng trọ Liên Chiểu Cho thuê phòng trọ Ngũ Hành Sơn"
    )
    ex_180 = extract_rule(raw_180)
    assert ex_180.street == "Mẹ Nhu"
    assert ex_180.district == "Thanh Khê"
    assert "Ngũ Hành Sơn" not in (ex_180.address or "")

    # 2. Bài 178: Trà Khê 8 (Ngũ Hành Sơn)
    raw_178 = (
        "Cho thuê phòng 12 trà khê 8 giá 2tr200/phòng (ở tối đa 3 bạn). "
        "Cho thuê phòng trọ Đ. Trà Khê 8, P. Ngũ Hành Sơn, Tp. Đà Nẵng | 307869489 | Meeyland "
        "Phản ánh tin đăng Cho thuê phòng trọ Liên Chiểu"
    )
    ex_178 = extract_rule(raw_178)
    assert ex_178.district == "Ngũ Hành Sơn"
    assert "Trà Khê" in (ex_178.street or "") or "Trà Khê" in (ex_178.address or "")

    # 3. Bài 261: Lỗ Giáng 8, Hòa Xuân, Cẩm Lệ
    raw_261 = (
        "Phòng trọ 20 đường Lỗ Giáng 8, hòa xuân, cẩm lệ. "
        "Giá thuê 1.6 triệu/tháng Diện tích 9 m² Phường Hòa Xuân, Cẩm Lệ, Đà Nẵng. "
        "Thông tin mô tả: Phòng mới, sạch, thoáng, Số 20 đường Lõ Giáng 8, Hòa xuân, Cẩm Lệ. "
        "Tin cùng khu vực: Hoàng Diệu, Liên Chiểu"
    )
    ex_261 = extract_rule(raw_261)
    assert ex_261.district == "Cẩm Lệ"
    assert "Lỗ Giáng" in (ex_261.street or "") or "Lỗ Giáng" in (ex_261.address or "")
    assert "Hoàng Diệu" not in (ex_261.address or "")

    # 4. Bài 247: CMT8 Gần ĐH Đông Á (Cẩm Lệ) kèm nhiễu cầu Nguyễn Văn Cừ ở cuối trang
    raw_247 = (
        "🔥 Phòng Trọ CMT8 Gần ĐH Đông Á – Chỉ Từ 2 Triệu/Tháng. "
        "Bất Động Sản Cho thuê Đà Nẵng Cẩm Lệ Nhà trọ, phòng trọ Phường Khuê Trung. "
        "Bất động sản tương tự dành cho bạn: Cho thuê căn hộ 2pn dương bá trạc quận 8 gần cầu nguyễn văn cừ"
    )
    ex_247 = extract_rule(raw_247)
    assert ex_247.district == "Cẩm Lệ"
    assert ex_247.street == "Cách Mạng Tháng Tám"
    assert "Nguyễn Văn Cừ" not in (ex_247.address or "")


def test_module1_geocoding_street_and_ward_accuracy():
    lat_mn, lng_mn = approx_location("Thanh Khê", "Mẹ Nhu, Thanh Khê, Đà Nẵng")
    # Đường Mẹ Nhu nằm gần 16.0638, 108.1795 (cách ĐH Bách Khoa ~3km, không phải 0.1km)
    assert 16.055 <= lat_mn <= 16.072
    assert 108.170 <= lng_mn <= 108.190

    lat_tk, lng_tk = approx_location("Ngũ Hành Sơn", "Trà Khê 8, Hòa Hải, Ngũ Hành Sơn, Đà Nẵng")
    assert 15.975 <= lat_tk <= 16.005
    assert 108.245 <= lng_tk <= 108.270

    lat_hx, lng_hx = approx_location("Cẩm Lệ", "Lỗ Giáng 8, Hòa Xuân, Cẩm Lệ, Đà Nẵng")
    assert 15.995 <= lat_hx <= 16.025
    assert 108.205 <= lng_hx <= 108.230


def test_module2_smart_monthly_cost_estimator():
    # Trường hợp 1: Phòng ghi "bao điện nước"
    l_included = Listing(
        title="Trọ sleep box - mẹ nhu - điều hoà 24/14 - bao điện nước",
        description="Chỉ 1,9 triệu/tháng – bao điện nước, free wifi",
        price=1_900_000,
        room_type="o_ghep",
        electricity_price=None,
        water_price=None,
    )
    mc1 = monthly_cost(l_included)
    labels1 = " | ".join(i["label"].lower() for i in mc1["items"])
    assert "bao" in labels1 or "miễn phí" in labels1 or "đã gồm" in labels1
    assert mc1["total"] <= 1_980_000

    # Trường hợp 2: Phòng chưa ghi giá điện nước -> ước tính theo mặt bằng sinh viên Đà Nẵng
    l_unlisted = Listing(
        title="Phòng trọ khép kín mới xây 25m2",
        description="Phòng đẹp thoáng mát, giờ giấc tự do",
        price=2_200_000,
        room_type="phong_tro",
        electricity_price=None,
        water_price=None,
    )
    mc2 = monthly_cost(l_unlisted)
    assert len(mc2["items"]) >= 4  # Tiền phòng + Điện ước tính + Nước ước tính + Wifi
    assert mc2["total"] > 2_200_000 + 80_000


def test_module3_amenities_synonyms_negation_and_source_dedup():
    text = (
        "Trọ sleep box - mẹ nhu - điều hoà 24/14 - bao điện nước. "
        "Trang bị bếp từ + lò vi sóng, khóa vân tay, camera, chỗ đậu xe rộng rãi, không nuôi thú cưng, không gác."
    )
    ams = find_amenities(text)
    assert "may_lanh" in ams
    assert "nau_an" in ams
    assert "van_tay" in ams
    assert "camera" in ams
    assert "de_xe" in ams
    assert "thu_cung" not in ams
    assert "gac_lung" not in ams
    assert "o_ghep" in find_room_types(text)

    # Khử trùng nguồn đăng có cùng URL hoặc bị nhân bản qua nhiều group / cùng nguồn
    s1 = ListingSource(
        source_name="AI Bot · FB Trọ Đà Nẵng #02 (trodanang)",
        url="http://web.facebook.com/groups/trodanang/posts/910203043/",
        raw_text="Còn 1 phòng trọ sinh viên giá rẻ đường Ngô Thì Nhậm, Hòa Khánh Bắc, quận Liên Chiểu",
    )
    s2 = ListingSource(
        source_name="AI Bot · FB Phòng Trọ Sinh Viên Đà Nẵng",
        url="https://www.facebook.com/groups/phongtrosinhviendanang/posts/910203043/",
        raw_text="Còn 1 phòng trọ sinh viên giá rẻ đường Ngô Thì Nhậm, Hòa Khánh Bắc, quận Liên Chiểu",
    )
    s3 = ListingSource(
        source_name="Meeyland Đà Nẵng",
        url="https://meeyland.com/cho-thue-phong-tro/other-room",
        raw_text="Cho thuê phòng trọ hoàn toàn khác tại đường Nguyễn Tri Phương Hải Châu",
    )
    deduped = deduplicate_sources([s1, s2, s3])
    assert len(deduped) == 1
    assert deduped[0].url == s1.url


def test_module4_multi_signal_risk_and_granular_quality():
    db = SessionLocal()
    try:
        l_broker = Listing(
            id=99991,
            title="Cho thuê phòng trọ giá rẻ hệ thống quản lý 50 phòng",
            description="Liên hệ chuyên viên tư vấn giỏ hàng hệ thống trọ sinh viên, cam kết hỗ trợ tìm phòng.",
            price=2_000_000,
            area=20.0,
            district="Thanh Khê",
            street="Mẹ Nhu",
            address="Mẹ Nhu, Thanh Khê, Đà Nẵng",
            lat=16.0638,
            lng=108.1795,
            room_type="phong_tro",
            amenities=["may_lanh", "wifi"],
            images=["https://example.com/1.jpg", "https://example.com/2.jpg"],
            electricity_price=None,
            water_price=None,
        )
        r = assess(db, l_broker)
        assert 5 <= r["score"] < 35
        assert r["level"] == "low"
        assert len(r["checks"]) >= 2

        q_minimal = quality(Listing(price=2_000_000, description="Phòng trọ", images=[]))
        q_rich = quality(
            Listing(
                price=2_500_000,
                area=25.0,
                district="Hải Châu",
                street="Lê Đình Lý",
                address="Kiệt 45 Lê Đình Lý, Hải Châu, Đà Nẵng",
                lat=16.051,
                lng=108.211,
                electricity_price=3500,
                water_price=50000,
                deposit_months=1,
                amenities=["may_lanh", "nong_lanh", "wc_rieng", "wifi", "gio_tu_do", "de_xe"],
                images=[f"https://example.com/{i}.jpg" for i in range(6)],
                description=" ".join(["Phòng mới xây sạch đẹp đầy đủ tiện nghi chính chủ"] * 15),
            )
        )
        assert q_rich - q_minimal >= 3.0
    finally:
        db.close()


def test_module5_similar_listings_ranking():
    target = Listing(
        id=1,
        title="Trọ sleep box Mẹ Nhu",
        price=1_900_000,
        area=20.0,
        district="Thanh Khê",
        room_type="o_ghep",
        lat=16.0638,
        lng=108.1795,
        amenities=["may_lanh", "wifi", "gio_tu_do"],
        images=["https://example.com/a.jpg"],
        quality_score=8.5,
    )
    cand_close_same_type = Listing(
        id=2,
        title="KTX Sleepbox Thanh Khê gần Bách Khoa",
        price=1_800_000,
        area=22.0,
        district="Thanh Khê",
        room_type="o_ghep",
        lat=16.0650,
        lng=108.1780,
        amenities=["may_lanh", "wifi", "gio_tu_do"],
        images=["https://example.com/b.jpg"],
        quality_score=8.8,
    )
    cand_far_diff_type = Listing(
        id=3,
        title="Căn hộ mini Ngũ Hành Sơn",
        price=2_200_000,
        area=35.0,
        district="Ngũ Hành Sơn",
        room_type="can_ho_mini",
        lat=15.9865,
        lng=108.2585,
        amenities=["ban_cong"],
        images=[],
        quality_score=6.0,
    )
    ranked = rank_similar_listings(target, [cand_far_diff_type, cand_close_same_type])
    assert ranked[0].id == 2


def test_module6_natural_language_query_parser_streets_and_wards():
    db = SessionLocal()
    try:
        schools = db.query(School).all()
        f1 = parse_rule("phòng 2tr mẹ nhu có điều hoà", schools)
        assert f1.budget_max == 2_200_000
        assert "may_lanh" in f1.amenities
        assert "Thanh Khê" in f1.districts
        assert f1.keywords and "mẹ nhu" in f1.keywords.lower()

        f2 = parse_rule("trọ hòa xuân dưới 2tr5", schools)
        assert f2.budget_max == 2_500_000
        assert "Cẩm Lệ" in f2.districts

        f3 = parse_rule("sleepbox gần bách khoa bao điện nước", schools)
        assert "o_ghep" in f3.room_types
        assert f3.school_id is not None
    finally:
        db.close()


def test_pipeline_rejects_expired_and_multi_year_old_posts():
    from app.pipeline import RawPost, is_expired_or_stale_post, process_raw

    expired_bds123 = (
        "Cho thuê phòng trọ giá siêu hời. Tin đăng này đã hết hạn Thông tin có thể không còn chính xác. "
        "Giá thuê 1.8 triệu/tháng Diện tích 30 m² 380 Phố Tôn Đức Thắng, Phường Hòa Minh, Liên Chiểu, Đà Nẵng "
        "Cập nhật: 3 năm trước Ngày đăng Thứ ba, 14:21 03/10/2023"
    )
    is_exp, reason = is_expired_or_stale_post(expired_bds123)
    assert is_exp is True
    assert "hết hạn" in reason.lower() or "cũ" in reason.lower()

    active_meeyland = (
        "Trọ sleep box - mẹ nhu - điều hoà 24/14 - bao điện nước. "
        "Cho thuê phòng trọ Đ. Mẹ Nhu, P. Thanh Khê, Tp. Đà Nẵng | Ngày đăng: 01/11/2026 "
        "Mô tả: Chỉ 1,9 triệu/tháng – bao điện nước. "
        "Phản ánh tin đăng: Bất động sản đã bán/ đã thuê/ đã sang nhượng"
    )
    is_exp2, _ = is_expired_or_stale_post(active_meeyland)
    assert is_exp2 is False

    db = SessionLocal()
    try:
        res = process_raw(
            db,
            RawPost(
                source_name="BDS123 · Phòng trọ Đà Nẵng",
                url="https://bds123.vn/cho-thue-phong-tro-gia-sieu-hoi-pr731600.html",
                text=expired_bds123,
            ),
        )
        assert res["status"] == "rejected"
    finally:
        db.close()


