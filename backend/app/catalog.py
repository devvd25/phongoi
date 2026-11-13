"""Danh mục dùng chung: tiện ích, khu vực, trường, loại phòng, từ khóa lừa đảo & từ điển địa lý Đà Nẵng."""

import re
import unicodedata


def strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def norm(text: str) -> str:
    """Chữ thường, bỏ dấu, gộp khoảng trắng: dùng để so khớp tiếng Việt có dấu và không dấu."""
    return re.sub(r"\s+", " ", strip_accents(text.lower())).strip()


AMENITIES: list[dict] = [
    {"key": "gac_lung", "label": "Gác lửng", "synonyms": ["gác lửng", "gác xép", "gác lững", "có gác", "gác cao", "gác đúc", "gác gỗ", "gác"]},
    {"key": "may_lanh", "label": "Máy lạnh", "synonyms": ["máy lạnh", "điều hòa", "điều hoà", "máy điều hòa", "máy điều hoà", "ml", "air conditioner"]},
    {"key": "nong_lanh", "label": "Nóng lạnh", "synonyms": ["nóng lạnh", "bình nóng lạnh", "máy nước nóng", "nước nóng", "nl"]},
    {"key": "wc_rieng", "label": "WC riêng", "synonyms": ["wc riêng", "vệ sinh riêng", "toilet riêng", "tolet riêng", "khép kín", "vệ sinh khép kín", "wc khép kín", "vsr", "wcr"]},
    {"key": "nau_an", "label": "Được nấu ăn", "synonyms": ["nấu ăn", "kệ bếp", "bếp riêng", "bếp chung", "khu bếp", "tủ bếp", "bàn bếp", "bếp từ", "bếp điện", "lò vi sóng", "cho nấu", "nấu nướng"]},
    {"key": "gio_tu_do", "label": "Giờ giấc tự do", "synonyms": ["giờ tự do", "giờ giấc tự do", "không chung chủ", "ko chung chủ", "tự do giờ giấc", "ra vào tự do", "24/24", "24/14", "24/7", "kcc", "gtd"]},
    {"key": "de_xe", "label": "Chỗ để xe", "synonyms": ["để xe", "gửi xe", "nhà xe", "chỗ để xe", "chỗ đậu xe", "sân để xe", "bãi xe", "bãi đỗ xe", "hầm để xe"]},
    {"key": "may_giat", "label": "Máy giặt", "synonyms": ["máy giặt", "giặt sấy", "khu giặt"]},
    {"key": "thu_cung", "label": "Nuôi thú cưng", "synonyms": ["thú cưng", "nuôi mèo", "nuôi chó", "nuôi pet", "cho nuôi thú", "pet friendly", "pet"]},
    {"key": "ban_cong", "label": "Ban công", "synonyms": ["ban công", "balcony", "sân thượng", "logia"]},
    {"key": "noi_that", "label": "Full nội thất", "synonyms": ["full nội thất", "đầy đủ nội thất", "nội thất", "full đồ", "giường tủ", "tủ lạnh", "tủ quần áo", "nệm", "furnished"]},
    {"key": "wifi", "label": "Wifi", "synonyms": ["wifi", "wi-fi", "wiffi", "wife", "internet", "mạng cáp quang"]},
    {"key": "camera", "label": "Camera an ninh", "synonyms": ["camera", "cam an ninh", "camera an ninh", "cctv"]},
    {"key": "van_tay", "label": "Khóa vân tay", "synonyms": ["vân tay", "khóa vân tay", "khoá vân tay", "cửa vân tay", "khóa từ", "thẻ từ"]},
]
AMENITY_KEYS = {a["key"] for a in AMENITIES}
AMENITY_LABEL = {a["key"]: a["label"] for a in AMENITIES}

# Tâm khu vực và giá trung vị tham khảo (triệu đồng) cho dữ liệu mẫu.
DISTRICTS: dict[str, dict] = {
    "Liên Chiểu": {"lat": 16.0717, "lng": 108.1500, "median": 1.8},
    "Thanh Khê": {"lat": 16.0640, "lng": 108.1880, "median": 2.3},
    "Hải Châu": {"lat": 16.0471, "lng": 108.2068, "median": 2.9},
    "Sơn Trà": {"lat": 16.0750, "lng": 108.2380, "median": 2.6},
    "Ngũ Hành Sơn": {"lat": 16.0010, "lng": 108.2530, "median": 2.5},
    "Cẩm Lệ": {"lat": 16.0150, "lng": 108.1950, "median": 2.0},
    "Hòa Vang": {"lat": 16.0300, "lng": 108.1100, "median": 1.5},
}

WARDS: dict[str, list[str]] = {
    "Liên Chiểu": ["Hòa Khánh Bắc", "Hòa Khánh Nam", "Hòa Minh", "Hòa Hiệp Nam", "Hòa Hiệp Bắc", "Hòa Khánh"],
    "Thanh Khê": ["Thanh Khê Tây", "Thanh Khê Đông", "Xuân Hà", "Tam Thuận", "Tân Chính", "Thạc Gián", "Vĩnh Trung", "An Khê", "Hòa Khê", "Chính Gián"],
    "Hải Châu": ["Hải Châu 1", "Hải Châu 2", "Thạch Thang", "Thanh Bình", "Thuận Phước", "Hòa Thuận Tây", "Hòa Thuận Đông", "Nam Dương", "Phước Ninh", "Bình Thuận", "Bình Hiên", "Hòa Cường Bắc", "Hòa Cường Nam", "Hòa Cường"],
    "Sơn Trà": ["An Hải Bắc", "An Hải Đông", "An Hải Tây", "Mân Thái", "Nại Hiên Đông", "Phước Mỹ", "Thọ Quang", "An Hải"],
    "Ngũ Hành Sơn": ["Mỹ An", "Bắc Mỹ An", "Khuê Mỹ", "Hòa Hải", "Hòa Quý"],
    "Cẩm Lệ": ["Khuê Trung", "Hòa Thọ Đông", "Hòa Thọ Tây", "Hòa An", "Hòa Phát", "Hòa Xuân", "Nam Hòa Xuân"],
    "Hòa Vang": ["Hòa Châu", "Hòa Tiến", "Hòa Phước", "Hòa Nhơn", "Hòa Phong", "Hòa Khương", "Hòa Sơn", "Hòa Liên", "Túy Loan"],
}

STREETS: dict[str, list[str]] = {
    "Liên Chiểu": [
        "Ngô Sĩ Liên", "Nguyễn Lương Bằng", "Âu Cơ", "Phạm Như Xương", "Tôn Đức Thắng",
        "Hoàng Văn Thái", "Nguyễn Văn Cừ", "Ngô Thì Nhậm", "Mê Linh", "Nguyễn Tất Thành",
        "Lạc Long Quân", "Nguyễn Chánh", "Đặng Dung", "Phan Văn Định", "Trần Cao Vân nối dài",
        "Hoàng Thị Loan", "Kinh Dương Vương", "Nguyễn Sinh Sắc", "Đoàn Phú Tứ", "Nam Cao",
    ],
    "Thanh Khê": [
        "Mẹ Nhu", "Hà Huy Tập", "Điện Biên Phủ", "Lê Độ", "Trần Cao Vân", "Hàm Nghi",
        "Nguyễn Tri Phương", "Lê Trọng Tấn", "Thái Thị Bôi", "Cù Chính Lan", "Huỳnh Ngọc Huệ",
        "Nguyễn Phước Nguyên", "Đỗ Quang", "Hùng Vương", "Ông Ích Khiêm", "Dũng Sĩ Thanh Khê",
    ],
    "Hải Châu": [
        "Lê Đình Lý", "Nguyễn Văn Linh", "Hoàng Diệu", "Núi Thành", "Xô Viết Nghệ Tĩnh",
        "Trưng Nữ Vương", "Phan Châu Trinh", "Lê Duẩn", "Quang Trung", "Đống Đa",
        "3 Tháng 2", "2 Tháng 9", "30 Tháng 4", "Tiểu La", "Nguyễn Hữu Thọ",
        "Lê Thanh Nghị", "Phan Đăng Lưu", "Huỳnh Tấn Phát", "Trần Phú", "Bạch Đằng",
    ],
    "Sơn Trà": [
        "Ngô Quyền", "Phạm Văn Đồng", "Lê Hữu Trác", "Hồ Nghinh", "Võ Nguyên Giáp",
        "Võ Văn Kiệt", "Nguyễn Văn Thoại", "Trần Hưng Đạo", "Khúc Hạo", "Dương Đình Nghệ",
        "Vương Thừa Vũ", "Loseby", "Morrison", "Lương Thế Vinh", "Nguyễn Công Trứ",
    ],
    "Ngũ Hành Sơn": [
        "Trà Khê 8", "Trà Khê", "Lê Văn Hiến", "Trần Đại Nghĩa", "Mai Đăng Chơn",
        "Châu Thị Vĩnh Tế", "Bà Huyện Thanh Quan", "Đỗ Bá", "Phan Tứ", "An Thượng 1",
        "An Thượng 2", "An Thượng 3", "An Thượng 4", "An Thượng", "Mỹ Đa Đông",
        "Mỹ Đa Tây", "Hoàng Kế Viêm", "Chương Dương", "Nam Kỳ Khởi Nghĩa", "Võ Chí Công",
    ],
    "Cẩm Lệ": [
        "Lỗ Giáng 8", "Lỗ Giáng", "Cách Mạng Tháng Tám", "Ông Ích Đường", "Lương Nhữ Hộc",
        "Trường Chinh", "Thăng Long", "Phạm Hùng", "Võ An Ninh", "Đô Đốc Lân",
        "Nguyễn Phước Lan", "Cồn Dầu", "Lê Quảng Chí", "Trần Nam Trung", "Bình Hòa",
        "Tôn Đản", "Lê Đại Hành", "Nguyễn Nhàn",
    ],
    "Hòa Vang": [
        "Quốc lộ 14B", "Trường Sơn", "Hoàng Văn Thái nối dài", "ĐT 602", "ĐT 605", "Phạm Hùng nối dài",
    ],
}

STREET_ALIASES: list[tuple[str, str, str]] = [
    (r"\blo\s+giang\s*8\b", "Lỗ Giáng 8", "Cẩm Lệ"),
    (r"\blo\s+giang\b", "Lỗ Giáng", "Cẩm Lệ"),
    (r"\btra\s+khe\s*8\b", "Trà Khê 8", "Ngũ Hành Sơn"),
    (r"\btra\s+khe\b", "Trà Khê", "Ngũ Hành Sơn"),
    (r"\bme\s+nhu\b", "Mẹ Nhu", "Thanh Khê"),
    (r"\b(?:cmt8|cach\s+mang\s+thang\s*8|cach\s+mang\s+thang\s+tam)\b", "Cách Mạng Tháng Tám", "Cẩm Lệ"),
    (r"\bxo\s+viet\s+nghe\s+tinh\b", "Xô Viết Nghệ Tĩnh", "Hải Châu"),
    (r"\bkdt\s+lakeside\b|\bduong\s+me\s+linh\b|\bme\s+linh\b", "Mê Linh", "Liên Chiểu"),
    (r"\b(?:duong|d\.|pho|kiet|hem)\s+ngu\s+hanh\s+son\b", "Ngũ Hành Sơn", "Ngũ Hành Sơn"),
    (r"\ban\s+thuong\s*\d*\b", "An Thượng", "Ngũ Hành Sơn"),
    (r"\bchau\s+thi\s+vinh\s+te\b", "Châu Thị Vĩnh Tế", "Ngũ Hành Sơn"),
    (r"\bngo\s+thi\s+nham\b", "Ngô Thì Nhậm", "Liên Chiểu"),
    (r"\bpham\s+nhu\s+xuong\b", "Phạm Như Xương", "Liên Chiểu"),
    (r"\bnguyen\s+luong\s+bang\b", "Nguyễn Lương Bằng", "Liên Chiểu"),
]

SCHOOLS: list[dict] = [
    {"name": "ĐH Bách khoa – ĐH Đà Nẵng", "short_name": "Bách khoa ĐN", "district": "Liên Chiểu", "lat": 16.0736, "lng": 108.1499,
     "aliases": ["bach khoa", "dhbk", "bk", "dut", "dai hoc bach khoa"]},
    {"name": "ĐH Sư phạm – ĐH Đà Nẵng", "short_name": "Sư phạm ĐN", "district": "Liên Chiểu", "lat": 16.0617, "lng": 108.1593,
     "aliases": ["su pham", "dhsp", "ued"]},
    {"name": "ĐH Kinh tế – ĐH Đà Nẵng", "short_name": "Kinh tế ĐN", "district": "Ngũ Hành Sơn", "lat": 16.0478, "lng": 108.2394,
     "aliases": ["kinh te", "dhkt", "due"]},
    {"name": "ĐH Duy Tân", "short_name": "Duy Tân", "district": "Hải Châu", "lat": 16.0602, "lng": 108.2133,
     "aliases": ["duy tan", "dtu"]},
    {"name": "ĐH Đông Á", "short_name": "Đông Á", "district": "Hải Châu", "lat": 16.0322, "lng": 108.2216,
     "aliases": ["dong a", "uda"]},
    {"name": "ĐH Ngoại ngữ – ĐH Đà Nẵng", "short_name": "Ngoại ngữ ĐN", "district": "Cẩm Lệ", "lat": 16.0335, "lng": 108.2085,
     "aliases": ["ngoai ngu", "ufl"]},
    {"name": "ĐH FPT Đà Nẵng", "short_name": "FPT ĐN", "district": "Ngũ Hành Sơn", "lat": 15.9686, "lng": 108.2606,
     "aliases": ["fpt"]},
]

LANDMARKS: list[dict] = [
    {"name": "Chợ Hòa Khánh", "lat": 16.0745, "lng": 108.1530},
    {"name": "Chợ Hàn", "lat": 16.0680, "lng": 108.2240},
    {"name": "Chợ Cồn", "lat": 16.0680, "lng": 108.2140},
    {"name": "Biển Nguyễn Tất Thành", "lat": 16.0790, "lng": 108.1700},
    {"name": "Biển Mỹ Khê", "lat": 16.0600, "lng": 108.2460},
    {"name": "Bến xe Trung tâm Đà Nẵng", "lat": 16.0560, "lng": 108.1740},
]

ROOM_TYPES = {"phong_tro": "Phòng trọ", "o_ghep": "Ở ghép", "studio": "Studio", "can_ho_mini": "Căn hộ mini"}

SCAM_KEYWORDS = [
    "chuyển cọc trước", "cọc trước", "giữ chỗ online", "không cần xem phòng", "chuyển khoản trước",
    "giá sốc", "chỉ hôm nay", "cọc giữ chỗ", "chuyển khoản giữ phòng",
]

REPORT_REASONS = {
    "deposit": "Yêu cầu cọc trước",
    "wrong_info": "Thông tin sai",
    "rented": "Phòng đã cho thuê",
    "duplicate": "Tin trùng lặp",
    "other": "Lý do khác",
}

_NEGATION_RE = re.compile(r"\b(?:khong|ko|chua|cam)(?:\s+[a-z0-9]+){0,2}\s+$")


def find_amenities(text: str) -> list[str]:
    n = f" {norm(text)} "
    found: list[str] = []
    for a in AMENITIES:
        matched_positive = False
        for syn in a["synonyms"]:
            s = norm(syn)
            for m in re.finditer(rf"(?<![a-z0-9]){re.escape(s)}(?![a-z0-9])", n):
                prefix = n[max(0, m.start() - 18) : m.start()]
                if _NEGATION_RE.search(prefix):
                    continue
                matched_positive = True
                break
            if matched_positive:
                break
        if matched_positive:
            found.append(a["key"])

    # Mô hình Sleepbox / KTX luôn có sẵn wifi và giờ giấc linh hoạt nếu không bị phủ định
    if re.search(r"\b(?:sleep\s*box|sleepbox|ktx|ky\s+tuc\s+xa)\b", n):
        for k in ("wifi", "gio_tu_do"):
            if k not in found:
                found.append(k)
    return found


def find_districts(text: str) -> list[str]:
    n = norm(text)
    out: list[str] = []
    for d in DISTRICTS:
        nd = norm(d)
        # Tránh nhầm tên đường Ngũ Hành Sơn thành quận nếu không đứng độc lập hoặc sau Quận/P.
        if re.search(rf"(?<![a-z0-9]){re.escape(nd)}(?![a-z0-9])", n):
            out.append(d)
    # Kiểm tra thêm tên Phường đặc trưng nếu chưa tìm thấy Quận
    if not out:
        for d, wards in WARDS.items():
            if any(re.search(rf"(?<![a-z0-9]){re.escape(norm(w))}(?![a-z0-9])", n) for w in wards):
                out.append(d)
    return list(dict.fromkeys(out))


def find_street_and_district(text: str) -> tuple[str | None, str | None, str | None]:
    """Trả về (street, ward, district) khớp chính xác nhất theo thứ tự ưu tiên xuất hiện trong văn bản."""
    n = norm(text)
    best_pos = 10**9
    best_street: str | None = None
    best_district: str | None = None

    # 1. Kiểm tra các alias đặc thù (CMT8, Mẹ Nhu, Trà Khê 8, Lỗ Giáng 8, Mê Linh...)
    for pat, canonical_street, d_name in STREET_ALIASES:
        if m := re.search(pat, n):
            if m.start() < best_pos:
                best_pos = m.start()
                best_street = canonical_street
                best_district = d_name

    # 2. Kiểm tra danh mục STREETS theo vị trí xuất hiện sớm nhất trong câu
    for d_name, streets in STREETS.items():
        for s in streets:
            ns = norm(s)
            if m := re.search(rf"(?<![a-z0-9]){re.escape(ns)}(?![a-z0-9])", n):
                if m.start() < best_pos:
                    best_pos = m.start()
                    best_street = s
                    best_district = d_name

    # 3. Kiểm tra Phường (Ward)
    best_ward: str | None = None
    ward_pos = 10**9
    ward_district: str | None = None
    for d_name, wards in WARDS.items():
        for w in wards:
            nw = norm(w)
            if m := re.search(rf"(?<![a-z0-9]){re.escape(nw)}(?![a-z0-9])", n):
                if m.start() < ward_pos:
                    ward_pos = m.start()
                    best_ward = w
                    ward_district = d_name

    # 4. Kiểm tra Quận trực tiếp (ví dụ: P. Thanh Khê, Quận Cẩm Lệ...)
    explicit_districts = find_districts(text)
    final_district = best_district or ward_district or (explicit_districts[0] if explicit_districts else None)
    # Nếu có Quận nói rõ trong câu mà đường tìm thấy lại ở Quận khác (trừ đường liên quận như CMT8, Điện Biên Phủ, Nguyễn Tất Thành, Ông Ích Khiêm)
    CROSS_DISTRICT_STREETS = {"Cách Mạng Tháng Tám", "Điện Biên Phủ", "Nguyễn Tất Thành", "Ông Ích Khiêm", "Nguyễn Văn Linh", "Trường Chinh"}
    if explicit_districts and best_district and best_district not in explicit_districts:
        if best_street in CROSS_DISTRICT_STREETS:
            final_district = explicit_districts[0]
        elif ward_district and ward_district in explicit_districts:
            final_district = ward_district
    return best_street, best_ward, final_district


def find_room_types(text: str) -> list[str]:
    n = norm(text)
    head = n[:120]
    out = []
    if re.search(r"\b(?:o\s+ghep|ghep|tim\s+nguoi\s+o\s+ghep|sleep\s*box|sleepbox|ktx|ky\s+tuc\s+xa|giuong\s+tang)\b", n):
        out.append("o_ghep")
    # Nếu tiêu đề nói rõ "Phòng trọ" / "Nhà trọ" (và không phải căn hộ/studio trên tiêu đề), không nhận nhầm từ khóa "căn hộ" ở phần mô tả phụ
    if re.search(r"\b(?:phong\s+tro|nha\s+tro)\b", head) and not re.search(r"\b(?:studio|can\s+ho|chung\s+cu|apartment)\b", head):
        return out
    if "studio" in n:
        out.append("studio")
    if re.search(r"can\s+ho\s+mini|chung\s+cu\s+mini|can\s+ho|apartment", n):
        out.append("can_ho_mini")
    return out
