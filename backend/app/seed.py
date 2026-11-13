"""Tạo dữ liệu mẫu cho Đà Nẵng:  python -m app.seed

Tài khoản thử nghiệm (chỉ dùng cho môi trường phát triển):
  admin@phongoi.vn    / Admin@2026      (quản trị)
  chutro@phongoi.vn   / Chutro@2026     (chủ trọ)
  sinhvien@phongoi.vn / Sinhvien@2026   (sinh viên)
"""

import hashlib
import random
from datetime import date, timedelta

from .catalog import AMENITY_LABEL, DISTRICTS, SCHOOLS, STREETS
from .db import Base, SessionLocal, engine, utcnow
from .geo import approx_location
from .config import settings
from .llm import model_name
from .models import (
    AIUsage, AppSetting, CrawlRun, CrawlSource, ExtractionIssue, Listing, ListingSource, ListingStat, NeedsProfile,
    Notification, PipelineRun, Report, SavedListing, School, SearchLog, User,
)
from .pricing import district_stats
from .risk import apply as apply_risk
from .risk import quality
from .source_registry import sync_source_registry
from .search import reindex_all
from .security import hash_password

ACCOUNTS = [
    ("admin@phongoi.vn", "Admin@2026", "Quản trị viên", "admin"),
    ("chutro@phongoi.vn", "Chutro@2026", "Trần Minh Tuấn", "landlord"),
    ("sinhvien@phongoi.vn", "Sinhvien@2026", "Nguyễn Vân Anh", "student"),
]
IMAGES = [f"/rooms/room-{i}.jpg" for i in range(1, 5)]
SOURCES = [
    ("AI Bot · FB Trọ Đà Nẵng #02 (trodanang)", "http://web.facebook.com/groups/trodanang/"),
    ("Chợ Tốt", "https://www.chotot.com/da-nang/thue-phong-tro"),
    ("phongtro123.com", "https://phongtro123.com/"),
]
DISTRICT_WEIGHTS = {"Liên Chiểu": 30, "Thanh Khê": 15, "Hải Châu": 15, "Sơn Trà": 10, "Ngũ Hành Sơn": 12, "Cẩm Lệ": 13, "Hòa Vang": 5}
ROOM_WEIGHTS = {"phong_tro": 60, "o_ghep": 15, "studio": 15, "can_ho_mini": 10}
AMENITY_P = {"may_lanh": .6, "nong_lanh": .7, "wc_rieng": .8, "gac_lung": .45, "nau_an": .7, "gio_tu_do": .55, "de_xe": .8, "wifi": .7,
             "may_giat": .25, "ban_cong": .2, "noi_that": .3, "camera": .35, "van_tay": .2, "thu_cung": .1}
SEASON = {6: 1.02, 7: 1.04, 8: 1.08, 9: 1.09, 10: 1.05}
TITLE_BITS = {
    "phong_tro": ["Phòng {gac}mới sơn, {f1}", "Phòng {gac}{f1}, {f2}", "Phòng sạch đẹp, {f1}"],
    "o_ghep": ["Phòng ở ghép 2 người, {f1}", "Tìm người ở ghép, {f1}"],
    "studio": ["Studio mới xây, {f1}", "Studio nhỏ, {f1}"],
    "can_ho_mini": ["Căn hộ mini {f1}, {f2}", "Căn hộ mini có ban công, {f1}"],
}
FEATURE_TEXT = {"gac_lung": "có gác lửng", "may_lanh": "máy lạnh mới", "nong_lanh": "có nóng lạnh", "wc_rieng": "WC riêng", "nau_an": "cho nấu ăn",
                "gio_tu_do": "giờ giấc tự do", "de_xe": "có chỗ để xe", "may_giat": "máy giặt riêng", "ban_cong": "có ban công",
                "noi_that": "full nội thất", "camera": "có camera an ninh", "van_tay": "khóa vân tay", "thu_cung": "cho nuôi mèo", "wifi": "wifi mạnh"}
SCAM_TEXT = [
    "Giá sốc chỉ hôm nay! Ai cần inbox, chuyển cọc trước 500k để giữ chỗ, không cần xem phòng.",
    "Phòng đẹp giá rẻ, cọc giữ chỗ online qua ví, chuyển khoản trước mới gửi địa chỉ.",
]


def pick(rnd: random.Random, weights: dict) -> str:
    return rnd.choices(list(weights), weights=list(weights.values()))[0]


def make_description(rnd, room_type, area, street, district, amen, elec, water, deposit, people) -> str:
    feats = ", ".join(FEATURE_TEXT[a] for a in amen[:6])
    lines = [
        f"Cho thuê {('phòng ở ghép' if room_type == 'o_ghep' else 'phòng')} {area:g}m2 tại {street}, {district}, Đà Nẵng.",
        f"Phòng {feats}." if feats else "Phòng thoáng mát, sạch sẽ.",
        f"Điện {elec // 1000}k{(elec % 1000) // 100 or ''}/số, nước {water // 1000}k/người, wifi 80k/phòng.",
        f"Cọc {deposit} tháng, hợp đồng tối thiểu 6 tháng. Ở tối đa {people} người.",
        rnd.choice(["Khu yên tĩnh, an ninh tốt, gần chợ và trạm xe buýt.", "Gần trường, tiện đi lại, xung quanh nhiều quán ăn sinh viên.",
                    "Chủ nhà thân thiện, ưu tiên sinh viên, xem phòng giờ hành chính."]),
    ]
    return " ".join(lines)


def make_title(rnd, room_type, amen) -> str:
    feats = [FEATURE_TEXT[a] for a in amen if a not in ("gac_lung", "wifi", "de_xe")] or ["thoáng mát"]
    t = rnd.choice(TITLE_BITS[room_type]).format(gac="gác lửng " if "gac_lung" in amen else "", f1=feats[0], f2=feats[1] if len(feats) > 1 else "gần chợ")
    return t[0].upper() + t[1:]


def add_listing(db, rnd, idx, *, district=None, street=None, kiet=None, room_type=None, area=None, price=None, amen=None,
                title=None, posted=None, status="active", owner=None, scam=False, fingerprint=None, n_images=None, sources=None):
    now = utcnow()
    district = district or pick(rnd, DISTRICT_WEIGHTS)
    street = street or rnd.choice(STREETS[district])
    room_type = room_type or pick(rnd, ROOM_WEIGHTS)
    if area is None:
        lo, hi = {"phong_tro": (14, 28), "o_ghep": (15, 24), "studio": (18, 30), "can_ho_mini": (24, 36)}[room_type]
        area = float(rnd.randint(lo, hi))
    if amen is None:
        amen = [a for a, p in AMENITY_P.items() if rnd.random() < p and not (a == "gac_lung" and room_type != "phong_tro")]
    if posted is None:
        days = rnd.randint(0, 90) if rnd.random() < 0.6 else rnd.randint(91, 365)
        posted = now - timedelta(days=days, hours=rnd.randint(0, 23))
    if price is None:
        base = DISTRICTS[district]["median"] * 1_000_000
        premium = len({"may_lanh", "noi_that", "wc_rieng", "ban_cong", "may_giat", "van_tay"} & set(amen))
        factor = {"phong_tro": 1.0, "o_ghep": 0.72, "studio": 1.15, "can_ho_mini": 1.3}[room_type]
        trend = 1 + 0.03 * (1 - (now - posted).days / 365)
        price = base * (area / 20) ** 0.5 * (1 + 0.035 * premium) * factor * SEASON.get(posted.month, 1.0) * trend * rnd.gauss(1, 0.07)
        if scam:
            price = base * rnd.uniform(0.35, 0.5)
        price = int(round(price / 50_000) * 50_000)
    kiet = kiet or f"Kiệt {rnd.randint(10, 320)}"
    address = f"{kiet} {street}, {district}, Đà Nẵng"
    lat, lng = approx_location(district, address)
    elec = rnd.choice([3000, 3500, 3500, 4000])
    water = rnd.choice([80_000, 100_000, 100_000, 120_000])
    deposit = rnd.choice([1, 1, 1, 2])
    people = {"o_ghep": rnd.randint(2, 4)}.get(room_type, rnd.choice([2, 2, 3]))
    desc = make_description(rnd, room_type, area, f"{kiet} {street}", district, amen, elec, water, deposit, people)
    if scam:
        desc = rnd.choice(SCAM_TEXT) + " " + desc
    n_img = n_images if n_images is not None else rnd.randint(3, 6)
    imgs = [IMAGES[(idx + k) % 4] for k in range(n_img)]
    l = Listing(
        title=title or make_title(rnd, room_type, amen), description=desc, price=price, area=area, district=district, street=street,
        address=address, lat=lat, lng=lng, room_type=room_type, max_people=people, amenities=amen, deposit_months=deposit,
        electricity_price=elec, water_price=water, wifi_price=80_000, images=imgs,
        image_fingerprint=fingerprint or hashlib.md5(f"seed-{idx}".encode()).hexdigest(), status=status, owner_id=owner.id if owner else None,
        poster_account_age_days=rnd.randint(1, 5) if scam else rnd.randint(40, 2000), posted_at=posted, created_at=posted,
    )
    l.ai_summary = [
        "Có " + ", ".join(AMENITY_LABEL[a].lower() for a in amen[:5]) if amen else "Phòng cơ bản, thoáng mát",
        f"Điện {elec:,}đ/kWh · nước {water:,}đ/người · wifi 80.000đ/phòng".replace(",", "."),
        f"Cọc {deposit} tháng, hợp đồng tối thiểu 6 tháng",
    ]
    srcs = sources if sources is not None else rnd.sample(SOURCES, rnd.choices([1, 2, 3], weights=[55, 30, 15])[0])
    for name, url in srcs:
        l.sources.append(ListingSource(source_name=name, url=url, posted_at=posted - timedelta(hours=rnd.randint(0, 48)), raw_text=desc))
    l.source_count = max(1, len(srcs))
    db.add(l)
    return l


def run() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    rnd = random.Random(2026)
    db = SessionLocal()
    now = utcnow()
    today = now.date()

    for s in SCHOOLS:
        db.add(School(**s))
    db.flush()
    users = {}
    for email, pw, name, role in ACCOUNTS:
        u = User(email=email, password_hash=hash_password(pw), full_name=name, role=role, created_at=now - timedelta(days=400 if role != "student" else 80))
        if role == "landlord":
            u.phone, u.phone_verified, u.address_verified, u.id_verification = "0905 *** 468", True, True, "pending"
            u.bio = "Khu trọ yên tĩnh, ưu tiên sinh viên Bách khoa, chủ ở gần, sửa chữa nhanh."
        if role == "student":
            u.school_id = 1
        db.add(u)
        users[role] = u
    db.flush()

    # Tin tiêu biểu dùng trong demo (giống thiết kế Figma).
    add_listing(db, rnd, 0, district="Liên Chiểu", street="Ngô Sĩ Liên", kiet="Kiệt 45", room_type="phong_tro", area=22.0, price=2_200_000,
                amen=["gac_lung", "may_lanh", "nong_lanh", "wc_rieng", "nau_an", "gio_tu_do", "de_xe", "wifi", "camera", "van_tay"],
                title="Phòng gác lửng full nội thất, cửa sổ thoáng", posted=now - timedelta(hours=2), n_images=6, sources=SOURCES)
    for i in range(1, 360):
        add_listing(db, rnd, i)
    scam_fp = hashlib.md5(b"scam-group").hexdigest()
    scams = []
    for i in range(18):
        extra = dict(district="Sơn Trà", street="Hồ Nghinh", area=30.0, price=900_000, title="Phòng 30 m² gần biển Mỹ Khê, chỉ 900 nghìn/tháng") if i == 0 else {}
        scams.append(add_listing(db, rnd, 400 + i, scam=True, fingerprint=scam_fp if i < 6 else None, posted=now - timedelta(days=rnd.randint(0, 20)),
                                 sources=[SOURCES[0]] if i % 2 == 0 else [SOURCES[1]], **extra))

    # Phòng của chủ trọ mẫu.
    landlord = users["landlord"]
    rooms_def = [
        ("101", "Gác lửng", 2_700_000, "active", 6, 30), ("102", "Gác lửng", 2_200_000, "rented", 6, 120), ("103", "Gác lửng", 2_200_000, "rented", 5, 150),
        ("201", "Ở ghép", 1_800_000, "rented", 5, 200), ("202", "Gác lửng", 2_200_000, "rented", 5, 180), ("203", "Studio", 2_400_000, "rented", 6, 90),
        ("204", "Ban công", 2_300_000, "pending", 2, 1), ("205", "Gác lửng", 2_200_000, "rented", 5, 210), ("301", "Gác lửng", 2_100_000, "rented", 5, 240),
        ("302", "Ban công", 2_400_000, "rented", 6, 100), ("303", "Gác lửng", 2_200_000, "rented", 5, 60), ("305", "Studio", 2_500_000, "active", 5, 18),
    ]
    rooms = []
    for k, (num, kind, price, status, n_img, age) in enumerate(rooms_def):
        rt = {"Ở ghép": "o_ghep", "Studio": "studio"}.get(kind, "phong_tro")
        amen = ["may_lanh", "nong_lanh", "wc_rieng", "nau_an", "gio_tu_do", "de_xe", "wifi", "camera"] + (["gac_lung"] if kind == "Gác lửng" else []) + (["ban_cong"] if kind == "Ban công" else [])
        r = add_listing(db, rnd, 500 + k, district="Liên Chiểu", street="Ngô Sĩ Liên", kiet="Kiệt 45", room_type=rt, area=float(rnd.choice([20, 22, 24])),
                        price=price, amen=amen, title=f"Phòng {num} · {kind}", posted=now - timedelta(days=age), status=status, owner=landlord,
                        n_images=n_img, sources=[("Tin chính chủ (Phòng Ơi)", "")])
        if num == "102":
            r.available_from = today + timedelta(days=15)
        rooms.append(r)
    db.flush()

    district_stats(db, force=True)
    for l in db.query(Listing).all():
        l.quality_score = quality(l)
        apply_risk(db, l)
    db.flush()

    # Thống kê lượt xem 60 ngày cho phòng của chủ trọ.
    for r in rooms:
        if r.status == "pending":
            continue
        tot_v = tot_c = 0
        for d in range(60):
            day = today - timedelta(days=d)
            imp = rnd.randint(28, 52) if r.status == "active" else rnd.randint(6, 14)
            if day.weekday() == 4:
                imp = int(imp * 1.4)
            views = max(1, int(imp * rnd.uniform(0.08, 0.12)))
            contacts = int(views * rnd.uniform(0.04, 0.1) + (1 if rnd.random() < 0.3 else 0))
            db.add(ListingStat(listing_id=r.id, day=day, impressions=imp, views=views, contacts=contacts, saves=1 if rnd.random() < 0.15 else 0))
            if d < 30:
                tot_v += views
                tot_c += contacts
        r.views, r.contacts = tot_v, tot_c

    # Sinh viên mẫu: hồ sơ nhu cầu, tin đã lưu, thông báo.
    student = users["student"]
    db.add(NeedsProfile(user_id=student.id, budget_min=1_500_000, budget_max=2_500_000, school_id=1, max_distance_km=2.0,
                        room_types=["phong_tro"], amenities=["gac_lung", "nau_an"], max_people=2, transport="xe_may", move_in="tháng 9"))
    first = db.query(Listing).filter_by(title="Phòng gác lửng full nội thất, cửa sổ thoáng").first()
    picks = [first] + db.query(Listing).filter(Listing.district == "Liên Chiểu", Listing.status == "active", Listing.risk_level == "low",
                                               Listing.id != first.id, Listing.owner_id.is_(None)).limit(3).all()
    for k, l in enumerate(picks):
        db.add(SavedListing(user_id=student.id, listing_id=l.id, price_at_save=l.price + (200_000 if k == 0 else 0), contacted=k == 1))
    db.add(SavedListing(user_id=student.id, listing_id=scams[3].id, price_at_save=scams[3].price))
    for kind, text, h in [("match", "3 phòng mới khớp hồ sơ nhu cầu của bạn", 0.2), ("price_drop", f"{first.title[:28]}… giảm còn 2.000.000đ", 1),
                          ("report", "Một tin bạn đã lưu bị báo cáo nghi lừa đảo, hãy cẩn trọng", 20), ("daily", "Gợi ý hằng ngày của bạn đã sẵn sàng", 26)]:
        db.add(Notification(user_id=student.id, kind=kind, text=text, read=h > 10, created_at=now - timedelta(hours=h)))

    # Thông báo cho chủ trọ và quản trị viên.
    by_num = {r.title.split(" · ")[0]: r for r in rooms}
    for kind, text, link, h in [
        ("contact", "Có sinh viên xem liên hệ Phòng 305", "/chu-tro/thong-ke", 0.5),
        ("pending", "Phòng 204 đang chờ duyệt, thường mất dưới 2 giờ", "/chu-tro/phong", 3),
        ("price_tip", "Phòng 101 cao hơn giá khu vực, xem gợi ý giá", "/chu-tro", 8),
        ("approved", "Tin Phòng 305 đã được duyệt và hiển thị", f"/phong/{by_num['Phòng 305'].id}", 30),
    ]:
        db.add(Notification(user_id=landlord.id, kind=kind, text=text, link=link, read=h > 10, created_at=now - timedelta(hours=h)))
    for kind, text, link, h in [
        ("report", "3 báo cáo mới nghi lừa đảo cọc trước", "/admin/kiem-duyet", 0.3),
        ("pending", "Tin mới chờ duyệt: Phòng 204 · Ban công", "/admin/kiem-duyet", 2),
        ("source_error", "Nguồn mogi.vn thu thập lỗi, kiểm tra cấu hình", "/admin/nguon", 5),
        ("budget", "Chi phí AI tháng này đã dùng 61% ngân sách", "/admin/chi-phi-ai", 28),
    ]:
        db.add(Notification(user_id=users["admin"].id, kind=kind, text=text, link=link, read=h > 10, created_at=now - timedelta(hours=h)))

    # Báo cáo từ sinh viên.
    labels = ["SV ĐH Kinh tế", "SV ĐH Duy Tân", "SV ĐH Sư phạm", "SV ĐH Bách khoa", "SV ĐH Đông Á", "SV ĐH FPT"]
    texts = {"deposit": "Chủ trọ bắt chuyển cọc 500 nghìn qua ví, không cho xem phòng trước.", "wrong_info": "Ảnh không đúng với phòng thực tế.",
             "rented": "Phòng đã cho thuê nhưng tin vẫn đăng.", "duplicate": "Tin đăng lặp lại nhiều lần.", "other": "Thông tin liên hệ không khớp."}
    for i in range(31):
        reason = rnd.choices(list(texts), weights=[42, 26, 16, 10, 6])[0]
        target = scams[i % len(scams)] if reason in ("deposit", "wrong_info") else rnd.choice(scams)
        status = "new" if i < 5 else "processing" if i < 8 else rnd.choice(["resolved", "resolved", "rejected"])
        db.add(Report(listing_id=target.id, reporter_label=rnd.choice(labels), reason=reason, description=texts[reason], status=status,
                      created_at=now - timedelta(hours=i * 20 + rnd.randint(0, 10))))
    db.flush()
    for s in scams:
        apply_risk(db, s)

    # Nguồn thu thập & lịch sử chạy. Nguồn bên thứ ba tạm dừng mặc định cho tới khi cấu hình selector và kiểm tra điều khoản.
    sync_source_registry(db)
    for h, (c, cl, ex, dd, sc, ix, dur) in enumerate([(1284, 842, 842, 530, 530, 486, 372), (1102, 790, 790, 470, 470, 441, 348), (1198, 801, 795, 480, 480, 451, 460),
                                                   (1076, 744, 744, 452, 452, 430, 355), (1150, 770, 770, 466, 466, 448, 360)]):
        db.add(PipelineRun(started_at=now - timedelta(hours=h, minutes=6), duration_s=dur, collected=c, cleaned=cl, extracted=ex, deduped=dd, scored=sc, indexed=ix,
                           status="partial" if h == 2 else "success"))
    for snip, reason in [("Cho thuê phòng giá thương lượng, ib để biết thêm chi tiết…", "Thiếu giá"), ("Phòng đẹp lắm ạ, ai cần inbox em nhé", "Thiếu thông tin"),
                         ("Tuyển người ở ghép nữ, 1tr5 bao điện nước, gần ĐH Kinh tế", "Cần xác nhận giá")]:
        db.add(ExtractionIssue(snippet=snip, reason=reason, payload={"price": None, "district": None}))

    # Lượt gọi AI theo ngày (tháng này và tháng trước), theo LLM đang cấu hình. Mô hình chạy cục bộ (Ollama) không tốn phí API.
    local = settings.llm_provider in ("ollama", "none")
    model = model_name() if settings.llm_provider != "none" else "qwen3:4b"
    start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    d = start
    while d <= today:
        wave = 1 + 0.25 * ((d.day % 7) / 7)
        for task, calls, tok, cost in [("extract", 840, 545, 26_500), ("query", 1920, 52, 8_000), ("summary", 160, 230, 2_650)]:
            k = wave * (0.9 if d < today.replace(day=1) else 1.0)
            db.add(AIUsage(day=d, task=task, model=model, calls=int(calls * k), tokens=int(calls * tok * k), cost_vnd=0 if local else round(cost * k)))
        d += timedelta(days=1)

    for key, value in {
        "dataset_meta": {"mode": "demo", "label": "Dữ liệu minh họa", "seeded": True},
        "ai_budget": {"monthly": 2_000_000, "alert_pct": 80, "auto_downgrade": True},
        "ai_cache": {"rate": 42},
        "eval_extraction": {"f1": 0.91, "json_valid": 99.2, "search_latency_s": 1.4},
        "eval_fields": {"fields": [{"field": "Giá thuê", "f1": 0.97}, {"field": "Diện tích", "f1": 0.95}, {"field": "Số điện thoại", "f1": 0.93},
                                   {"field": "Địa chỉ", "f1": 0.89}, {"field": "Tiện ích", "f1": 0.86}, {"field": "Giờ giấc, quy định", "f1": 0.81}]},
        "prompt_versions": {"versions": [{"name": "v1 · Zero-shot", "f1": 0.82, "cost": 64, "json_valid": 96.1, "current": False},
                                         {"name": "v2 · Few-shot", "f1": 0.88, "cost": 81, "json_valid": 98.7, "current": False},
                                         {"name": "v3 · Few-shot + schema", "f1": 0.91, "cost": 79, "json_valid": 99.2, "current": True}]},
        "amenity_filters": {"hidden": ["thu_cung"]},
    }.items():
        db.add(AppSetting(key=key, value=value))

    # Nhật ký tìm kiếm cho thống kê từ khóa.
    samples = [{"amenities": ["gac_lung"], "school_id": 1, "budget_max": 2_500_000}, {"amenities": ["nau_an"], "school_id": 1},
               {"budget_max": 2_500_000}, {"amenities": ["gio_tu_do"]}, {"amenities": ["gac_lung", "may_lanh"]}]
    for i in range(240):
        db.add(SearchLog(query="(mẫu)", filters=rnd.choice(samples), engine="rule", result_count=rnd.randint(10, 80),
                         created_at=now - timedelta(hours=rnd.randint(0, 24 * 29))))
    db.commit()
    indexed = reindex_all(db)
    # Keep the CLI usable on Windows terminals configured with a legacy code page.
    print(f"Created {db.query(Listing).count()} demo listings, {len(SCHOOLS)} schools, {len(ACCOUNTS)} sample accounts. ES: {indexed} documents.")
    db.close()


if __name__ == "__main__":
    run()
