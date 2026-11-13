from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = DOCS / "report_assets"
OUTPUT = DOCS / "Bao_cao_phan_tich_thiet_ke_xay_dung_kiem_thu_Phong_Oi.docx"
ASSETS.mkdir(parents=True, exist_ok=True)

NAVY = "17365D"
BLUE = "2F5597"
PALE_BLUE = "EAF2F8"
PALE_ORANGE = "FCE4D6"
ORANGE = "F05A0B"
LIGHT = "F7F9FC"
GRID = "D9D9D9"
TEXT = "1F2937"
GREEN = "2E7D32"
RED = "C62828"


def font_path(bold: bool = False) -> str:
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf"),
    ]
    return str(next(p for p in candidates if p.exists()))


def pfont(size: int, bold: bool = False):
    return ImageFont.truetype(font_path(bold), size=size)


def arrow(draw: ImageDraw.ImageDraw, a: tuple[int, int], b: tuple[int, int], color="#52677D", width=5):
    draw.line([a, b], fill=color, width=width)
    import math

    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    length = 22
    spread = 0.55
    p1 = (b[0] - length * math.cos(angle - spread), b[1] - length * math.sin(angle - spread))
    p2 = (b[0] - length * math.cos(angle + spread), b[1] - length * math.sin(angle + spread))
    draw.polygon([b, p1, p2], fill=color)


def rounded_box(draw, xy, title, lines=(), fill="#F7F9FC", outline="#2F5597", title_fill=None, title_size=36, text_size=27):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=24, fill=fill, outline=outline, width=4)
    if title_fill:
        draw.rounded_rectangle((x1, y1, x2, min(y2, y1 + 72)), radius=24, fill=title_fill, outline=outline, width=4)
        draw.rectangle((x1, y1 + 45, x2, y1 + 72), fill=title_fill)
        draw.text(((x1 + x2) / 2, y1 + 36), title, anchor="mm", font=pfont(title_size, True), fill="white")
        yy = y1 + 92
    else:
        draw.text(((x1 + x2) / 2, y1 + 42), title, anchor="mm", font=pfont(title_size, True), fill="#17365D")
        yy = y1 + 78
    for line in lines:
        draw.text((x1 + 24, yy), line, font=pfont(text_size), fill="#24364B")
        yy += text_size + 13


def save_canvas(name: str, size=(2100, 1400)):
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    return img, draw, ASSETS / name


def create_use_case():
    img, d, path = save_canvas("use_case.png", (2100, 1450))
    d.text((1050, 55), "SƠ ĐỒ USE CASE TỔNG QUÁT", anchor="mm", font=pfont(52, True), fill="#17365D")
    d.rounded_rectangle((390, 130, 1710, 1370), radius=35, outline="#A7B9CC", width=4, fill="#FBFCFE")
    d.text((1050, 165), "Hệ thống Phòng Ơi", anchor="mm", font=pfont(38, True), fill="#2F5597")

    def actor(x, y, label):
        d.ellipse((x - 30, y - 85, x + 30, y - 25), outline="#17365D", width=5)
        d.line((x, y - 25, x, y + 75), fill="#17365D", width=5)
        d.line((x - 55, y + 10, x + 55, y + 10), fill="#17365D", width=5)
        d.line((x, y + 75, x - 48, y + 140), fill="#17365D", width=5)
        d.line((x, y + 75, x + 48, y + 140), fill="#17365D", width=5)
        d.text((x, y + 182), label, anchor="mm", font=pfont(31, True), fill="#17365D")

    actors = [(170, 350, "Khách"), (170, 790, "Sinh viên"), (1930, 430, "Chủ trọ"), (1930, 900, "Quản trị viên")]
    for a in actors:
        actor(*a)

    cases = [
        (720, 280, "Tìm kiếm và xem bản đồ"), (1280, 280, "Xem chi tiết và liên hệ"),
        (720, 500, "Đăng nhập và quản lý tài khoản"), (1280, 500, "Lưu tin và nhận gợi ý"),
        (720, 720, "Báo cáo tin bất thường"), (1280, 720, "Đăng và quản lý phòng"),
        (720, 940, "Quản lý nguồn thu thập"), (1280, 940, "Kiểm duyệt và danh mục"),
        (720, 1160, "Phân tích giá và rủi ro"), (1280, 1160, "Theo dõi pipeline và AI"),
    ]
    for x, y, label in cases:
        d.ellipse((x - 235, y - 70, x + 235, y + 70), fill="#EAF2F8", outline="#2F5597", width=4)
        d.text((x, y), label, anchor="mm", font=pfont(27, True), fill="#17365D")

    links = [
        ((235, 350), (485, 280)), ((235, 350), (1045, 280)),
        ((235, 790), (485, 280)), ((235, 790), (485, 500)), ((235, 790), (1045, 500)), ((235, 790), (485, 720)), ((235, 790), (485, 1160)),
        ((1865, 430), (1515, 720)), ((1865, 430), (1045, 280)), ((1865, 430), (1045, 500)),
        ((1865, 900), (955, 940)), ((1865, 900), (1515, 940)), ((1865, 900), (1515, 1160)), ((1865, 900), (485, 720)),
    ]
    for a, b in links:
        d.line([a, b], fill="#9AA9B8", width=3)
    img.save(path, quality=95)
    return path


def create_architecture():
    img, d, path = save_canvas("architecture.png", (2100, 1420))
    d.text((1050, 55), "KIẾN TRÚC TỔNG THỂ", anchor="mm", font=pfont(52, True), fill="#17365D")
    rounded_box(d, (90, 145, 2010, 305), "Lớp trình bày", ["React 18 + TypeScript + Vite + Tailwind CSS", "TanStack Query · React Router · Leaflet/OpenStreetMap · Recharts"], fill="#FFF7F2", outline="#F05A0B", title_fill="#F05A0B")
    arrow(d, (1050, 305), (1050, 380))
    rounded_box(d, (90, 380, 2010, 590), "Lớp API và nghiệp vụ", ["FastAPI · Pydantic · SQLAlchemy · JWT/RBAC", "Public API · Student API · Landlord API · Admin API · Swagger/OpenAPI"], fill="#EAF2F8", outline="#2F5597", title_fill="#2F5597")
    arrow(d, (1050, 590), (1050, 670))
    boxes = [
        (90, 670, 570, 990, "Dữ liệu giao dịch", ["PostgreSQL", "SQLite khi phát triển", "Alembic migration"]),
        (610, 670, 1070, 990, "Tìm kiếm", ["Elasticsearch", "Full text tiếng Việt", "Geo point và bộ lọc"]),
        (1110, 670, 1560, 990, "Xử lý nền", ["Celery + Redis", "Thu thập theo lịch", "Pipeline và thông báo"]),
        (1600, 670, 2010, 990, "AI và học máy", ["Ollama/Gemini/OpenAI", "Trích xuất và hiểu truy vấn", "scikit-learn"]),
    ]
    for x1, y1, x2, y2, title, lines in boxes:
        rounded_box(d, (x1, y1, x2, y2), title, lines, fill="#F7F9FC", outline="#6B7F93", title_fill="#52677D", title_size=30, text_size=25)
    for x in (330, 840, 1335, 1805):
        arrow(d, (1050, 590), (x, 670), width=4)
    rounded_box(d, (210, 1100, 920, 1340), "Nguồn dữ liệu", ["Scrapy/Playwright · API JSON · tin chính chủ", "Robots.txt · rate limit · phê duyệt điều khoản"], fill="#F4FAF4", outline="#2E7D32", title_fill="#2E7D32", title_size=32)
    rounded_box(d, (1180, 1100, 1890, 1340), "Dịch vụ bản đồ và email", ["OpenStreetMap · Leaflet · định vị trình duyệt", "SMTP · thông báo trong hệ thống"], fill="#F4FAF4", outline="#2E7D32", title_fill="#2E7D32", title_size=32)
    arrow(d, (720, 1100), (1260, 990), width=4)
    arrow(d, (1540, 1100), (1540, 990), width=4)
    img.save(path, quality=95)
    return path


def create_erd():
    img, d, path = save_canvas("erd.png", (2300, 1600))
    d.text((1150, 48), "SƠ ĐỒ THỰC THỂ LIÊN KẾT RÚT GỌN", anchor="mm", font=pfont(50, True), fill="#17365D")
    entities = {
        "User": (80, 150, ["PK id", "email · role", "school_id", "verification"]),
        "School": (820, 150, ["PK id", "name · district", "lat · lng"]),
        "NeedsProfile": (80, 500, ["PK/FK user_id", "budget", "school_id", "districts · amenities"]),
        "SavedListing": (80, 850, ["PK user_id", "PK listing_id", "price_at_save"]),
        "Listing": (820, 500, ["PK id", "owner_id", "price · district", "lat · lng", "risk · quality · status"]),
        "ListingSource": (820, 1050, ["PK id", "FK listing_id", "source_name · url"]),
        "Report": (1540, 500, ["PK id", "FK listing_id", "FK user_id", "reason · status"]),
        "ListingStat": (1540, 850, ["PK id", "FK listing_id", "day · views", "contacts · saves"]),
        "CrawlSource": (1540, 150, ["PK id", "profile_id", "kind · connector", "status · approval"]),
        "CrawlRun": (1540, 1200, ["PK id", "FK source_id", "status", "new · dup · errors"]),
    }
    rects = {}
    for name, (x, y, lines) in entities.items():
        w, h = 560, 255
        rects[name] = (x, y, x + w, y + h)
        rounded_box(d, rects[name], name, lines, fill="#F8FAFC", outline="#2F5597", title_fill="#17365D", title_size=31, text_size=25)

    def relation(a, b, label, card_a="1", card_b="N"):
        ra, rb = rects[a], rects[b]
        ca = ((ra[0] + ra[2]) // 2, (ra[1] + ra[3]) // 2)
        cb = ((rb[0] + rb[2]) // 2, (rb[1] + rb[3]) // 2)
        # choose nearest sides
        if abs(ca[0] - cb[0]) > abs(ca[1] - cb[1]):
            pa = (ra[2] if ca[0] < cb[0] else ra[0], ca[1])
            pb = (rb[0] if ca[0] < cb[0] else rb[2], cb[1])
        else:
            pa = (ca[0], ra[3] if ca[1] < cb[1] else ra[1])
            pb = (cb[0], rb[1] if ca[1] < cb[1] else rb[3])
        d.line([pa, pb], fill="#687A8C", width=4)
        d.text((pa[0] + 12, pa[1] - 12), card_a, font=pfont(22, True), fill="#C2410C")
        d.text((pb[0] - 25, pb[1] - 12), card_b, font=pfont(22, True), fill="#C2410C")
        mx, my = (pa[0] + pb[0]) // 2, (pa[1] + pb[1]) // 2
        d.rounded_rectangle((mx - 105, my - 25, mx + 105, my + 25), radius=12, fill="white")
        d.text((mx, my), label, anchor="mm", font=pfont(20), fill="#52677D")

    relation("School", "User", "theo học", "1", "N")
    relation("User", "NeedsProfile", "sở hữu", "1", "0..1")
    relation("User", "SavedListing", "lưu", "1", "N")
    relation("Listing", "SavedListing", "được lưu", "1", "N")
    relation("User", "Listing", "đăng", "1", "N")
    relation("Listing", "ListingSource", "có nguồn", "1", "N")
    relation("Listing", "Report", "bị báo cáo", "1", "N")
    relation("Listing", "ListingStat", "có thống kê", "1", "N")
    relation("CrawlSource", "CrawlRun", "thực thi", "1", "N")
    img.save(path, quality=95)
    return path


def create_activity():
    img, d, path = save_canvas("activity.png", (1900, 1600))
    d.text((950, 50), "ACTIVITY DIAGRAM TÌM VÀ LƯU PHÒNG", anchor="mm", font=pfont(48, True), fill="#17365D")
    cx = 950
    d.ellipse((cx - 32, 120, cx + 32, 184), fill="#17365D")
    stages = [
        (230, "Nhập câu hỏi tự nhiên hoặc chọn bộ lọc"),
        (390, "Frontend gửi yêu cầu tìm kiếm"),
        (550, "Backend chuẩn hóa và kiểm chứng bộ lọc"),
        (710, "Truy vấn Elasticsearch hoặc SQL"),
    ]
    last_y = 184
    for y, label in stages:
        arrow(d, (cx, last_y), (cx, y - 52))
        d.rounded_rectangle((550, y - 52, 1350, y + 52), radius=28, fill="#EAF2F8", outline="#2F5597", width=4)
        d.text((cx, y), label, anchor="mm", font=pfont(29, True), fill="#17365D")
        last_y = y + 52
    arrow(d, (cx, last_y), (cx, 850))
    d.polygon([(cx, 850), (cx + 170, 960), (cx, 1070), (cx - 170, 960)], fill="#FFF7F2", outline="#F05A0B")
    d.text((cx, 960), "Có kết quả\nphù hợp?", anchor="mm", align="center", font=pfont(30, True), fill="#9A3412")
    d.text((1160, 915), "Có", font=pfont(25, True), fill="#2E7D32")
    arrow(d, (1120, 960), (1450, 960), color="#2E7D32")
    d.rounded_rectangle((1450, 900, 1840, 1020), radius=25, fill="#F4FAF4", outline="#2E7D32", width=4)
    d.text((1645, 960), "Xem danh sách\nvà bản đồ", anchor="mm", align="center", font=pfont(28, True), fill="#1B5E20")
    d.text((720, 915), "Không", font=pfont(25, True), fill="#C62828")
    arrow(d, (780, 960), (440, 960), color="#C62828")
    d.rounded_rectangle((60, 900, 440, 1020), radius=25, fill="#FFF5F5", outline="#C62828", width=4)
    d.text((250, 960), "Gợi ý nới bộ lọc\nhoặc đổi truy vấn", anchor="mm", align="center", font=pfont(27, True), fill="#9B1C1C")
    arrow(d, (1645, 1020), (1645, 1130))
    d.rounded_rectangle((1390, 1130, 1890, 1245), radius=25, fill="#EAF2F8", outline="#2F5597", width=4)
    d.text((1640, 1187), "Xem chi tiết, giá,\nrủi ro và nguồn", anchor="mm", align="center", font=pfont(27, True), fill="#17365D")
    arrow(d, (1640, 1245), (1640, 1350))
    d.rounded_rectangle((1390, 1350, 1890, 1465), radius=25, fill="#FFF7F2", outline="#F05A0B", width=4)
    d.text((1640, 1407), "Lưu tin hoặc\nliên hệ chủ trọ", anchor="mm", align="center", font=pfont(28, True), fill="#9A3412")
    arrow(d, (1640, 1465), (1640, 1515))
    d.ellipse((1605, 1515, 1675, 1585), outline="#17365D", width=5)
    d.ellipse((1618, 1528, 1662, 1572), fill="#17365D")
    arrow(d, (250, 1020), (250, 1465), color="#C62828")
    arrow(d, (250, 1465), (780, 1465), color="#C62828")
    d.text((530, 1428), "quay lại nhập điều kiện", anchor="mm", font=pfont(22), fill="#9B1C1C")
    img.save(path, quality=95)
    return path


def create_sequence():
    img, d, path = save_canvas("sequence.png", (2200, 1550))
    d.text((1100, 55), "SEQUENCE DIAGRAM TÌM KIẾM BẰNG NGÔN NGỮ TỰ NHIÊN", anchor="mm", font=pfont(46, True), fill="#17365D")
    actors = [(170, "Sinh viên"), (570, "React Client"), (980, "FastAPI"), (1410, "LLM và luật"), (1840, "Search Engine")]
    top = 160
    for x, label in actors:
        d.rounded_rectangle((x - 150, top, x + 150, top + 100), radius=22, fill="#EAF2F8", outline="#2F5597", width=4)
        d.text((x, top + 50), label, anchor="mm", font=pfont(28, True), fill="#17365D")
        d.line((x, top + 100, x, 1460), fill="#91A4B7", width=3)
    messages = [
        (330, 170, 570, "1  Nhập yêu cầu tìm phòng"),
        (450, 570, 980, "2  POST /api/search/parse"),
        (570, 980, 1410, "3  Phân tích câu truy vấn"),
        (690, 1410, 980, "4  JSON bộ lọc đề xuất"),
        (810, 980, 980, "5  Pydantic và luật kiểm chứng"),
        (930, 980, 1840, "6  POST /api/search với bộ lọc"),
        (1050, 1840, 980, "7  Danh sách, pin bản đồ, thống kê"),
        (1170, 980, 570, "8  SearchResult JSON"),
        (1290, 570, 170, "9  Hiển thị danh sách và bản đồ"),
    ]
    for y, x1, x2, label in messages:
        color = "#2F5597" if x2 >= x1 else "#2E7D32"
        if x1 == x2:
            d.line((x1, y, x1 + 130, y), fill=color, width=4)
            d.line((x1 + 130, y, x1 + 130, y + 55), fill=color, width=4)
            arrow(d, (x1 + 130, y + 55), (x1, y + 55), color=color, width=4)
            d.text((x1 + 145, y + 18), label, font=pfont(23), fill="#24364B")
        else:
            arrow(d, (x1, y), (x2, y), color=color, width=4)
            d.text(((x1 + x2) // 2, y - 24), label, anchor="mm", font=pfont(23), fill="#24364B")
    img.save(path, quality=95)
    return path


def create_class_diagram():
    img, d, path = save_canvas("class_model.png", (2300, 1600))
    d.text((1150, 50), "THIẾT KẾ LỚP VÀ MÔ HÌNH DỮ LIỆU", anchor="mm", font=pfont(48, True), fill="#17365D")
    classes = {
        "User": (70, 150, ["id: int", "email: str", "role: str"], ["authenticate()", "authorize()"]),
        "NeedsProfile": (70, 600, ["budget_min/max", "districts[]", "amenities[]"], ["update()"]),
        "Listing": (820, 150, ["price: int", "location", "risk_score", "quality_score"], ["calculateRisk()", "serializeCard()"]),
        "SearchService": (820, 680, ["filters", "query", "engine"], ["parseQuery()", "search()", "rank()"]),
        "CrawlSource": (1580, 150, ["kind", "start_url", "config", "health_score"], ["approve()", "run()"]),
        "PipelineService": (1580, 680, ["rawPost", "runStatus"], ["clean()", "extract()", "dedupe()", "index()"]),
        "RecommendationService": (820, 1190, ["profile", "listing"], ["score()", "explain()"]),
    }
    rects = {}
    for name, (x, y, attrs, methods) in classes.items():
        w, h = 620, 340
        rects[name] = (x, y, x + w, y + h)
        d.rounded_rectangle(rects[name], radius=20, fill="#FBFCFE", outline="#2F5597", width=4)
        d.rectangle((x, y, x + w, y + 70), fill="#17365D")
        d.text((x + w / 2, y + 35), name, anchor="mm", font=pfont(31, True), fill="white")
        d.line((x, y + 70, x + w, y + 70), fill="#2F5597", width=3)
        yy = y + 90
        for value in attrs:
            d.text((x + 24, yy), "+ " + value, font=pfont(25), fill="#24364B")
            yy += 38
        divider = y + 215
        d.line((x, divider, x + w, divider), fill="#A7B9CC", width=3)
        yy = divider + 18
        for value in methods:
            d.text((x + 24, yy), "+ " + value, font=pfont(24), fill="#17365D")
            yy += 36
    relations = [
        ("User", "NeedsProfile", "1  sở hữu  0..1"),
        ("User", "Listing", "1  đăng  N"),
        ("NeedsProfile", "SearchService", "cung cấp điều kiện"),
        ("Listing", "SearchService", "được truy vấn"),
        ("CrawlSource", "PipelineService", "khởi tạo"),
        ("PipelineService", "Listing", "tạo hoặc cập nhật"),
        ("SearchService", "RecommendationService", "xếp hạng"),
        ("Listing", "RecommendationService", "đầu vào"),
    ]
    for a, b, label in relations:
        ra, rb = rects[a], rects[b]
        ca = ((ra[0] + ra[2]) // 2, (ra[1] + ra[3]) // 2)
        cb = ((rb[0] + rb[2]) // 2, (rb[1] + rb[3]) // 2)
        pa = (ca[0], ra[3] if ca[1] < cb[1] else ra[1]) if abs(ca[1] - cb[1]) >= abs(ca[0] - cb[0]) else (ra[2] if ca[0] < cb[0] else ra[0], ca[1])
        pb = (cb[0], rb[1] if ca[1] < cb[1] else rb[3]) if abs(ca[1] - cb[1]) >= abs(ca[0] - cb[0]) else (rb[0] if ca[0] < cb[0] else rb[2], cb[1])
        arrow(d, pa, pb, color="#7C8DA0", width=3)
        mx, my = (pa[0] + pb[0]) // 2, (pa[1] + pb[1]) // 2
        d.rounded_rectangle((mx - 130, my - 24, mx + 130, my + 24), radius=12, fill="white")
        d.text((mx, my), label, anchor="mm", font=pfont(19), fill="#52677D")
    img.save(path, quality=95)
    return path


def set_cell_shading(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def set_table_borders(table, color=GRID, size="6"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), size)
        node.set(qn("w:color"), color)


def add_table(doc, headers: list[str], rows: Iterable[Iterable[str]], widths: list[float] | None = None, font_size=9.2):
    rows = [list(map(str, r)) for r in rows]
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    prevent_row_split(hdr)
    for i, value in enumerate(headers):
        cell = hdr.cells[i]
        set_cell_shading(cell, NAVY)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(cell)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(value)
        run.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        run.font.size = Pt(font_size)
        if widths:
            cell.width = Inches(widths[i])
    for ridx, row in enumerate(rows):
        new_row = table.add_row()
        prevent_row_split(new_row)
        cells = new_row.cells
        for i, value in enumerate(row):
            cell = cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell)
            if ridx % 2:
                set_cell_shading(cell, "F5F8FC")
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            if i == 0 and len(headers) > 2:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(value)
            r.font.size = Pt(font_size)
            if widths:
                cell.width = Inches(widths[i])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def set_run_font(run, name="Times New Roman", size=12, bold=None, color=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_body(doc, text: str, bold_lead: str | None = None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Cm(1)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.keep_together = True
    if bold_lead and text.startswith(bold_lead):
        r1 = p.add_run(bold_lead)
        set_run_font(r1, bold=True)
        r2 = p.add_run(text[len(bold_lead):])
        set_run_font(r2)
    else:
        r = p.add_run(text)
        set_run_font(r)
    return p


def add_bullets(doc, items: Iterable[str]):
    items = list(items)
    for index, item in enumerate(items):
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.first_line_indent = Cm(-0.35)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = index < len(items) - 1
        r = p.add_run(item)
        set_run_font(r)


def add_caption(doc, text: str):
    p = doc.add_paragraph(style="Caption")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_together = True
    r = p.add_run(text)
    set_run_font(r, size=10, bold=False)
    r.italic = True
    return p


def add_figure(doc, path: Path, caption: str, width=6.3):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_together = True
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width))
    add_caption(doc, caption)


def add_field(paragraph, instruction: str, placeholder: str = ""):
    run = paragraph.add_run()
    fld_char = OxmlElement("w:fldChar")
    fld_char.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char, instr, separate, text, end])


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def heading(doc, text: str, level: int):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.keep_with_next = True
    return p


def build_document():
    figures = [create_use_case(), create_architecture(), create_erd(), create_activity(), create_sequence(), create_class_diagram()]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.3)
    sec.right_margin = Cm(2.0)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.25
    normal.paragraph_format.space_after = Pt(6)
    for style_name, size, before, after in (("Title", 22, 0, 12), ("Heading 1", 16, 14, 8), ("Heading 2", 14, 10, 6), ("Heading 3", 12.5, 8, 4)):
        st = styles[style_name]
        st.font.name = "Times New Roman"
        st._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        st._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        st._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.keep_with_next = True
    styles["Title"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_ppr = styles["Title"]._element.get_or_add_pPr()
    title_border = title_ppr.find(qn("w:pBdr"))
    if title_border is not None:
        title_ppr.remove(title_border)

    # Cover
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("TRƯỜNG ĐẠI HỌC ĐÔNG Á")
    set_run_font(r, size=15, bold=True)
    p.paragraph_format.space_after = Pt(50)
    logo = ROOT / "frontend" / "public" / "brand" / "logo-full.png"
    if logo.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(logo), width=Inches(2.1))
        p.paragraph_format.space_after = Pt(28)
    title = doc.add_paragraph(style="Title")
    title.add_run("BÁO CÁO PHÂN TÍCH THIẾT KẾ XÂY DỰNG VÀ KIỂM THỬ HỆ THỐNG PHÒNG ƠI")
    title_direct_border = title._p.get_or_add_pPr().find(qn("w:pBdr"))
    if title_direct_border is not None:
        title._p.get_or_add_pPr().remove(title_direct_border)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(38)
    rr = subtitle.add_run("Hệ thống tổng hợp và phân tích tin đăng phòng trọ ứng dụng trí tuệ nhân tạo hỗ trợ sinh viên tại Đà Nẵng")
    set_run_font(rr, size=14, bold=True)
    info = add_table(doc, ["Thành viên", "Lớp"], [
        ("Đặng Công Vũ", "ST23D"), ("Lương Chí Bảo", "ST23D"), ("Nguyễn Đình Nhàng", "ST23D"), ("Phan Trần Xuân Huy", "ST23D")
    ], widths=[4.7, 1.4], font_size=11)
    info.rows[0].cells[0].merge(info.rows[0].cells[0])
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(35)
    r = p.add_run("Đà Nẵng 2026")
    set_run_font(r, size=13, bold=True)

    # Header / footer from all pages; title page header remains subtle.
    header = sec.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = header.add_run("BÁO CÁO HỆ THỐNG PHÒNG ƠI")
    set_run_font(hr, size=8, color="6B7280")
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run("Trang ")
    set_run_font(fr, size=9)
    add_field(footer, "PAGE")

    page_break(doc)
    heading(doc, "MỤC LỤC", 1)
    toc = doc.add_paragraph()
    add_field(toc, 'TOC \\o "1-3" \\h \\z \\u', "Mở tài liệu trong Microsoft Word và chọn Update Field để cập nhật mục lục")
    add_body(doc, "Tài liệu mô tả phiên bản hệ thống được đối chiếu trực tiếp với mã nguồn và cơ sở dữ liệu vận hành tại thời điểm ngày 12 tháng 11 năm 2026. Phạm vi gồm phân tích yêu cầu, thiết kế hệ thống, lựa chọn công nghệ, RESTful API, kế hoạch kiểm thử và kết quả đánh giá hiện trạng.")

    page_break(doc)
    heading(doc, "2 PHÂN TÍCH YÊU CẦU", 1)
    add_body(doc, "Hệ thống Phòng Ơi phục vụ bài toán tìm phòng trọ cho sinh viên tại Đà Nẵng. Dữ liệu được tổng hợp từ nguồn công khai đã được phê duyệt, API đối tác và tin chính chủ; sau đó được chuẩn hóa, gộp trùng, chấm rủi ro và đưa vào chức năng tìm kiếm, bản đồ và gợi ý cá nhân hóa.")

    heading(doc, "2.1 Tác nhân hệ thống", 2)
    add_table(doc, ["Tác nhân", "Mục tiêu", "Chức năng chính"], [
        ("Khách", "Khảo sát nguồn phòng trước khi đăng ký", "Xem trang chủ, tìm kiếm, bản đồ, chi tiết tin, giá thị trường và đăng ký tài khoản"),
        ("Sinh viên", "Tìm phòng phù hợp ngân sách và trường học", "Khai báo nhu cầu, tìm bằng ngôn ngữ tự nhiên, lưu và so sánh tin, nhận gợi ý, báo cáo tin"),
        ("Chủ trọ", "Đăng và quản lý phòng chính chủ", "Đăng/sửa phòng, tải ảnh, kiểm tra giá, xem thống kê lượt xem và liên hệ, cập nhật hồ sơ"),
        ("Quản trị viên", "Vận hành dữ liệu và bảo đảm chất lượng", "Quản lý nguồn, phê duyệt pháp lý, chạy thu thập, kiểm duyệt, xử lý báo cáo, danh mục và chi phí AI"),
        ("Dịch vụ thu thập", "Đưa dữ liệu ngoài vào hệ thống", "Scrapy, Playwright, API JSON; tuân thủ robots.txt, rate limit và kiểm tra URL công khai"),
        ("Dịch vụ AI và tìm kiếm", "Hiểu văn bản và truy xuất dữ liệu", "LLM/Ollama/Gemini/OpenAI, Elasticsearch, bộ luật dự phòng và mô hình scikit-learn"),
    ], widths=[1.15, 2.0, 3.25], font_size=9.0)

    heading(doc, "2.2 Sơ đồ Use Case", 2)
    add_body(doc, "Sơ đồ Use Case phân tách rõ ba vai trò đăng nhập và các chức năng công khai. Phân quyền được kiểm tra ở cả giao diện React và API FastAPI; backend là lớp quyết định cuối cùng thông qua JWT và cơ chế kiểm tra vai trò.")
    add_figure(doc, figures[0], "Hình 2.1 Sơ đồ Use Case tổng quát của hệ thống", width=5.05)

    heading(doc, "2.3 Yêu cầu chức năng", 2)
    add_table(doc, ["Mã", "Nhóm", "Yêu cầu chức năng", "Tác nhân"], [
        ("FR01", "Tài khoản", "Đăng ký, đăng nhập, đăng xuất, đặt lại và đổi mật khẩu", "Mọi người dùng"),
        ("FR02", "Tài khoản", "Xác thực JWT và phân quyền student, landlord, admin", "Hệ thống"),
        ("FR03", "Tìm kiếm", "Tìm theo ngân sách, khu vực, diện tích, loại phòng, tiện ích và khoảng cách", "Khách, sinh viên"),
        ("FR04", "AI tìm kiếm", "Chuyển câu tiếng Việt tự nhiên thành bộ lọc có cấu trúc và kiểm chứng bằng luật", "Khách, sinh viên"),
        ("FR05", "Bản đồ", "Hiển thị vị trí phòng, trường học, vị trí hiện tại trên OpenStreetMap", "Khách, sinh viên"),
        ("FR06", "Tin đăng", "Xem giá, chi phí, nguồn gốc, điểm chất lượng và mức rủi ro", "Khách, sinh viên"),
        ("FR07", "Cá nhân hóa", "Lưu hồ sơ nhu cầu và xếp hạng phòng theo mức phù hợp", "Sinh viên"),
        ("FR08", "Tương tác", "Lưu, bỏ lưu, so sánh, ghi nhận liên hệ và gửi phản hồi gợi ý", "Sinh viên"),
        ("FR09", "An toàn", "Báo cáo tin sai, đã thuê, trùng lặp hoặc yêu cầu đặt cọc đáng ngờ", "Khách, sinh viên"),
        ("FR10", "Thông báo", "Thông báo tin phù hợp, giảm giá, báo cáo và trạng thái kiểm duyệt", "Người dùng đăng nhập"),
        ("FR11", "Chủ trọ", "Đăng, sửa, làm mới, đổi trạng thái và tải tối đa 12 ảnh mỗi phòng", "Chủ trọ"),
        ("FR12", "AI chủ trọ", "Tự điền thông tin từ mô tả và ước lượng khoảng giá", "Chủ trọ"),
        ("FR13", "Thống kê", "Theo dõi hiển thị, lượt xem, liên hệ, lượt lưu và tỷ lệ chuyển đổi", "Chủ trọ"),
        ("FR14", "Thu thập", "Quản lý registry nguồn, selector, lịch, số trang và giới hạn tốc độ", "Quản trị viên"),
        ("FR15", "Tuân thủ", "Lưu biên bản phê duyệt điều khoản, robots.txt và tự thu hồi khi đổi URL", "Quản trị viên"),
        ("FR16", "Pipeline", "Thu thập, làm sạch, trích xuất, gộp trùng, chấm rủi ro và lập chỉ mục", "Hệ thống"),
        ("FR17", "Kiểm duyệt", "Duyệt, ẩn, bỏ cảnh báo hoặc chặn tin; xử lý báo cáo", "Quản trị viên"),
        ("FR18", "Danh mục", "Quản lý tiện ích, trường học, từ đồng nghĩa và từ khóa lừa đảo", "Quản trị viên"),
        ("FR19", "Vận hành", "Theo dõi chi phí AI, trạng thái dịch vụ, sức khỏe nguồn và lượt chạy", "Quản trị viên"),
        ("FR20", "Dữ liệu cá nhân", "Xuất dữ liệu cá nhân và xóa tài khoản không phải quản trị", "Người dùng đăng nhập"),
    ], widths=[0.55, 1.0, 3.95, 1.0], font_size=8.5)

    heading(doc, "2.4 Yêu cầu phi chức năng", 2)
    add_table(doc, ["Mã", "Thuộc tính", "Yêu cầu và tiêu chí"], [
        ("NFR01", "Hiệu năng", "Tìm kiếm thông thường hướng tới phản hồi dưới 2 giây; truy vấn có LLM dưới 5 giây; hỗ trợ phân trang và lazy loading giao diện"),
        ("NFR02", "Bảo mật", "Mật khẩu băm bcrypt; JWT có hạn; RBAC tại API; chặn URL nội bộ, credential nhúng và SSRF trong crawler"),
        ("NFR03", "Độ tin cậy", "Có fallback SQL khi Elasticsearch không sẵn sàng và fallback luật khi LLM lỗi hoặc trả JSON sai"),
        ("NFR04", "An toàn dữ liệu", "Alembic quản lý schema; quan hệ xóa dây chuyền cho dữ liệu phụ thuộc; production không tự tạo schema"),
        ("NFR05", "Khả dụng", "Giao diện responsive cho máy tính và điện thoại; có chế độ sáng/tối; thông báo trạng thái và lỗi bằng tiếng Việt"),
        ("NFR06", "Khả năng mở rộng", "Tách React, FastAPI, PostgreSQL, Elasticsearch, Redis/Celery và worker thành các dịch vụ Docker"),
        ("NFR07", "Bảo trì", "Mã nguồn chia module theo miền nghiệp vụ; kiểu dữ liệu TypeScript; schema Pydantic; kiểm thử backend và frontend"),
        ("NFR08", "Tuân thủ", "Nguồn ngoài mặc định cần kiểm tra điều khoản và robots.txt; rate limit một request mỗi miền; nguồn cần đối tác không được tự động bật"),
        ("NFR09", "Riêng tư", "Chỉ lưu dữ liệu cần thiết; người dùng có thể xuất và xóa dữ liệu; production yêu cầu secret đủ mạnh"),
        ("NFR10", "Quan sát", "Ghi CrawlRun, PipelineRun, AIUsage, health score, số lỗi liên tiếp và thông báo sự cố nguồn"),
    ], widths=[0.65, 1.35, 4.55], font_size=9.0)

    page_break(doc)
    heading(doc, "3 THIẾT KẾ HỆ THỐNG", 1)
    heading(doc, "3.1 Kiến trúc tổng thể", 2)
    add_body(doc, "Hệ thống áp dụng kiến trúc nhiều lớp và triển khai theo dịch vụ. React chịu trách nhiệm trình bày; FastAPI cung cấp nghiệp vụ và RESTful API; PostgreSQL là nguồn dữ liệu chính; Elasticsearch tăng tốc tìm kiếm; Celery và Redis xử lý tác vụ nền; crawler và các dịch vụ AI được cô lập khỏi giao diện người dùng.")
    add_figure(doc, figures[1], "Hình 3.1 Kiến trúc tổng thể của hệ thống")
    add_table(doc, ["Lớp", "Trách nhiệm", "Thành phần"], [
        ("Trình bày", "Hiển thị, điều hướng, quản lý trạng thái máy khách", "React, TypeScript, TanStack Query, Leaflet, Recharts"),
        ("API", "Xác thực, phân quyền, kiểm tra dữ liệu và điều phối nghiệp vụ", "FastAPI, Pydantic, JWT, SQLAlchemy"),
        ("Nghiệp vụ AI", "Hiểu truy vấn, trích xuất, gợi ý, giá và rủi ro", "LLM có fallback luật, scikit-learn"),
        ("Dữ liệu", "Lưu dữ liệu chuẩn hóa, tìm kiếm và cache hàng đợi", "PostgreSQL/SQLite, Elasticsearch, Redis"),
        ("Tích hợp", "Thu thập nguồn ngoài, email và tác vụ định kỳ", "Scrapy, Playwright, Celery, SMTP"),
    ], widths=[1.1, 3.0, 2.4], font_size=9.2)

    heading(doc, "3.2 Thiết kế cơ sở dữ liệu", 2)
    add_body(doc, "Mô hình dữ liệu lấy Listing làm trung tâm. Một tin có thể gắn nhiều nguồn gốc để phục vụ gộp trùng và truy vết; User liên kết với hồ sơ nhu cầu, tin đã lưu, thông báo, báo cáo và tin chính chủ. Nhóm bảng CrawlSource, CrawlRun và PipelineRun tách dữ liệu vận hành khỏi dữ liệu phòng trọ.")
    add_figure(doc, figures[2], "Hình 3.2 Sơ đồ ERD rút gọn")
    add_table(doc, ["Nhóm bảng", "Bảng chính", "Mục đích"], [
        ("Người dùng", "users, password_resets, needs_profiles", "Tài khoản, bảo mật và nhu cầu tìm phòng"),
        ("Tin đăng", "listings, listing_sources, listing_stats", "Dữ liệu phòng chuẩn hóa, nguồn gốc và tương tác theo ngày"),
        ("Tương tác", "saved_listings, notifications, reports, recommendation_feedback", "Lưu tin, thông báo, báo cáo và phản hồi"),
        ("Thu thập", "crawl_sources, crawl_runs, pipeline_runs, extraction_issues", "Cấu hình nguồn, lịch sử chạy và lỗi trích xuất"),
        ("AI và cấu hình", "ai_usage, catalog_items, app_settings, search_logs", "Chi phí AI, danh mục động, cấu hình và nhật ký truy vấn"),
    ], widths=[1.25, 2.7, 2.55], font_size=9.0)

    heading(doc, "3.3 Thiết kế luồng nghiệp vụ", 2)
    add_body(doc, "Luồng tìm phòng bắt đầu từ câu hỏi tự nhiên hoặc bộ lọc. Backend chuẩn hóa điều kiện, chỉ chấp nhận giá trị có trong danh mục, truy vấn dữ liệu và trả về cả danh sách lẫn pin bản đồ. Khi không có kết quả, giao diện yêu cầu người dùng nới điều kiện thay vì tự tạo tin không tồn tại.")
    add_figure(doc, figures[3], "Hình 3.3 Activity Diagram của nghiệp vụ tìm và lưu phòng")
    add_body(doc, "Đối với dữ liệu nguồn ngoài, luồng nền gồm kiểm tra trạng thái phê duyệt, xác thực URL công khai, thu thập theo rate limit, làm sạch, trích xuất, gộp trùng, chấm rủi ro, lưu PostgreSQL và đồng bộ Elasticsearch. Nguồn lỗi liên tiếp được giảm điểm sức khỏe và có thể tự tạm dừng.")

    heading(doc, "3.4 Thiết kế giao tiếp Client Server", 2)
    add_body(doc, "Client không gọi trực tiếp LLM hoặc Elasticsearch. Mọi yêu cầu đi qua FastAPI để áp dụng xác thực, schema và luật kiểm chứng. Cách thiết kế này ngăn khóa API xuất hiện trên trình duyệt và bảo đảm kết quả tìm kiếm luôn đến từ dữ liệu đã lưu.")
    add_figure(doc, figures[4], "Hình 3.4 Sequence Diagram của tìm kiếm bằng ngôn ngữ tự nhiên")

    heading(doc, "3.5 Thiết kế lớp dữ liệu", 2)
    add_body(doc, "Các lớp ORM phản ánh thực thể nghiệp vụ, còn các service module triển khai hành vi tìm kiếm, pipeline, gợi ý, giá và rủi ro. Cấu trúc này tránh đặt toàn bộ logic trong route và cho phép kiểm thử độc lập các hàm xử lý.")
    add_table(doc, ["Lớp hoặc service", "Trách nhiệm chính"], [
        ("User và NeedsProfile", "Lưu danh tính, vai trò và điều kiện tìm phòng của sinh viên"),
        ("Listing", "Biểu diễn phòng đã chuẩn hóa, vị trí, giá, chất lượng và rủi ro"),
        ("CrawlSource", "Lưu cấu hình tích hợp, trạng thái phê duyệt và sức khỏe nguồn"),
        ("SearchService", "Kiểm chứng bộ lọc, truy vấn dữ liệu và sắp xếp kết quả"),
        ("PipelineService", "Làm sạch, trích xuất, gộp trùng, chấm điểm và lập chỉ mục"),
        ("RecommendationService", "Tính điểm phù hợp và giải thích lý do gợi ý"),
    ], widths=[2.1, 4.25], font_size=9.0)
    add_figure(doc, figures[5], "Hình 3.5 Thiết kế lớp và mô hình dữ liệu rút gọn")

    page_break(doc)
    heading(doc, "4 XÂY DỰNG ỨNG DỤNG", 1)
    heading(doc, "4.1 Lựa chọn công nghệ", 2)
    add_table(doc, ["Hạng mục", "Công nghệ", "Lý do lựa chọn"], [
        ("Frontend", "React 18, TypeScript, Vite", "Component hóa giao diện, kiểm tra kiểu tĩnh và thời gian build nhanh"),
        ("UI", "Tailwind CSS, Lucide, Framer Motion", "Thiết kế responsive, nhất quán và có trạng thái tương tác rõ ràng"),
        ("Dữ liệu client", "TanStack Query", "Cache, đồng bộ trạng thái server và quản lý loading/error"),
        ("Bản đồ", "Leaflet và OpenStreetMap", "Không yêu cầu API key cho lớp bản đồ cơ bản và phù hợp bản đồ phòng trọ"),
        ("Backend", "FastAPI, Pydantic", "API bất đồng bộ, sinh OpenAPI tự động và kiểm tra dữ liệu chặt chẽ"),
        ("ORM và migration", "SQLAlchemy 2, Alembic", "Mô hình dữ liệu rõ ràng, hỗ trợ PostgreSQL và migration có phiên bản"),
        ("Cơ sở dữ liệu", "PostgreSQL, SQLite phát triển", "PostgreSQL cho production; SQLite giúp chạy nhanh cục bộ"),
        ("Tìm kiếm", "Elasticsearch 8", "Full text tiếng Việt, bộ lọc và truy vấn vị trí; có fallback SQL"),
        ("Tác vụ nền", "Celery, Redis", "Thu thập định kỳ và tách tác vụ dài khỏi request web"),
        ("Crawler", "Scrapy, Playwright", "Hỗ trợ HTML tĩnh và trang động, cấu hình robots.txt và rate limit"),
        ("AI", "Ollama, Gemini, OpenAI compatible", "Cho phép mô hình cục bộ hoặc dịch vụ ngoài; luôn có bộ luật dự phòng"),
        ("Học máy", "scikit-learn, joblib", "Huấn luyện mô hình giá và phân loại với quy trình Python thống nhất"),
        ("Đóng gói", "Docker Compose, Nginx", "Triển khai đồng bộ frontend, API, database, search và worker"),
    ], widths=[1.2, 2.15, 3.15], font_size=8.8)
    source_screen = ROOT / "artifacts" / "sources-rental-portals.png"
    if source_screen.exists():
        add_figure(doc, source_screen, "Hình 4.1 Giao diện quản lý nguồn thu thập trong hệ thống", width=4.7)

    heading(doc, "4.2 Tích hợp hệ thống RESTful API", 2)
    add_body(doc, "FastAPI hiện công bố 76 route dưới tiền tố /api. API dùng JSON cho dữ liệu nghiệp vụ, multipart/form-data cho tải ảnh và Bearer JWT cho chức năng cần đăng nhập. Mã trạng thái chính gồm 200/201 khi thành công, 401 khi chưa đăng nhập, 403 khi sai vai trò, 404 khi không tồn tại, 409 khi xung đột và 422 khi dữ liệu không hợp lệ.")
    add_table(doc, ["Nhóm", "Method", "Endpoint", "Chức năng", "Quyền"], [
        ("Auth", "POST", "/api/auth/register", "Đăng ký tài khoản", "Công khai"),
        ("Auth", "POST", "/api/auth/login", "Đăng nhập và nhận JWT", "Công khai"),
        ("Auth", "POST", "/api/auth/forgot", "Yêu cầu đặt lại mật khẩu", "Công khai"),
        ("Tìm kiếm", "POST", "/api/search/parse", "Phân tích câu truy vấn tự nhiên", "Công khai"),
        ("Tìm kiếm", "POST", "/api/search", "Tìm phòng và trả pin bản đồ", "Công khai"),
        ("Tin đăng", "GET", "/api/listings/{id}", "Xem chi tiết tin", "Công khai"),
        ("Thị trường", "POST", "/api/market/estimate", "Ước lượng khoảng giá", "Công khai"),
        ("Sinh viên", "PUT", "/api/me/needs", "Cập nhật hồ sơ nhu cầu", "Student"),
        ("Sinh viên", "GET", "/api/recommendations", "Lấy danh sách gợi ý", "Student"),
        ("Sinh viên", "POST", "/api/me/saved/{id}", "Lưu tin", "Student"),
        ("Sinh viên", "POST", "/api/listings/{id}/report", "Báo cáo tin", "Tùy chọn JWT"),
        ("Chủ trọ", "POST", "/api/landlord/rooms", "Đăng phòng mới", "Landlord/Admin"),
        ("Chủ trọ", "PATCH", "/api/landlord/rooms/{id}", "Sửa phòng và trạng thái", "Landlord/Admin"),
        ("Chủ trọ", "POST", "/api/landlord/upload", "Tải ảnh phòng", "Landlord/Admin"),
        ("Chủ trọ", "POST", "/api/landlord/autofill", "AI tự điền từ mô tả", "Landlord/Admin"),
        ("Admin", "GET", "/api/admin/sources", "Danh sách nguồn và lịch sử chạy", "Admin"),
        ("Admin", "POST", "/api/admin/sources/{id}/approve", "Phê duyệt điều khoản và robots", "Admin"),
        ("Admin", "POST", "/api/admin/sources/run-enabled", "Chạy các nguồn đủ điều kiện", "Admin"),
        ("Admin", "POST", "/api/admin/ingest", "Nhận dữ liệu từ crawler", "Ingest token"),
        ("Admin", "POST", "/api/admin/moderation/{id}", "Kiểm duyệt tin", "Admin"),
        ("Admin", "PUT", "/api/admin/ai-budget", "Cập nhật ngân sách AI", "Admin"),
        ("Vận hành", "GET", "/api/health", "Kiểm tra DB, search và LLM", "Công khai"),
    ], widths=[0.7, 0.6, 2.0, 2.35, 0.85], font_size=7.8)
    heading(doc, "4.2.1 Quy ước tích hợp", 3)
    add_bullets(doc, [
        "Frontend dùng một hàm api chung để gắn JWT, mã hóa JSON và chuẩn hóa thông báo lỗi từ backend.",
        "Pydantic giới hạn độ dài, khoảng giá trị và tập giá trị hợp lệ trước khi dữ liệu đi vào nghiệp vụ.",
        "Endpoint theo vai trò sử dụng dependency require_role; không tin vào kiểm tra điều hướng ở frontend.",
        "Crawler gửi dữ liệu qua ingest token riêng, không dùng JWT tài khoản người dùng.",
        "Tài liệu Swagger được FastAPI tạo tự động tại /docs trong môi trường chạy API.",
    ])

    heading(doc, "6 KIỂM THỬ VÀ ĐÁNH GIÁ", 1)
    heading(doc, "6.1 Kế hoạch kiểm thử", 2)
    add_body(doc, "Kế hoạch kiểm thử kết hợp unit test, integration test, kiểm tra kiểu tĩnh, build production và kiểm thử trình duyệt. Dữ liệu kiểm thử phải tách khỏi cơ sở dữ liệu vận hành; mỗi test giao diện cần xóa localStorage và unmount component để tránh trạng thái đăng nhập rò rỉ giữa các ca.")
    add_table(doc, ["TC", "Phạm vi", "Kịch bản", "Kết quả mong đợi"], [
        ("TC01", "Xác thực", "Đăng nhập đúng và sai mật khẩu", "Trả JWT khi đúng; 401 khi sai"),
        ("TC02", "Phân quyền", "Student truy cập API admin", "Backend trả 403"),
        ("TC03", "Tìm kiếm", "Tìm phòng dưới ngân sách tại Đà Nẵng", "Chỉ trả tin phù hợp và pin hợp lệ"),
        ("TC04", "NLP", "Nhập câu có giá, trường và tiện ích", "Bộ lọc JSON đúng; luật loại giá trị không có bằng chứng"),
        ("TC05", "Bản đồ", "Cho phép định vị và chọn marker", "Hiện vị trí người dùng, phòng và popup"),
        ("TC06", "Gợi ý", "Sinh viên có hồ sơ nhu cầu", "Kết quả có điểm match và lý do"),
        ("TC07", "Chủ trọ", "Đăng phòng hợp lệ và tải ảnh", "Tin ở trạng thái pending; ảnh đúng loại và kích thước"),
        ("TC08", "Giá", "Kiểm tra giá theo khu vực", "Trả low, mid, high và verdict"),
        ("TC09", "Thu thập", "Chạy nguồn đã duyệt", "Tạo CrawlRun và cập nhật số mới, trùng, lỗi"),
        ("TC10", "Tuân thủ", "Bật nguồn chưa duyệt hoặc thiếu selector", "API từ chối 422"),
        ("TC11", "SSRF", "Đăng URL localhost, private IP hoặc credential", "API/crawler chặn trước khi kết nối"),
        ("TC12", "Gộp trùng", "Nạp hai tin cùng địa chỉ, giá và nội dung gần nhau", "Không tạo bản ghi Listing trùng"),
        ("TC13", "Migration", "Nâng schema database mới", "Alembic upgrade head thành công"),
        ("TC14", "Frontend", "Chạy Vitest, typecheck và build", "Test độc lập, không lỗi TypeScript, build thành công"),
        ("TC15", "E2E", "Đăng nhập ba vai trò và đi qua luồng chính", "Không lỗi console; API và UI đồng nhất"),
    ], widths=[0.55, 1.15, 2.75, 2.15], font_size=8.3)

    heading(doc, "6.2 Kết quả đánh giá", 2)
    add_body(doc, "Kết quả dưới đây được chạy trực tiếp trên codebase ngày 12 tháng 11 năm 2026. Báo cáo giữ nguyên cả các ca chưa đạt để phản ánh đúng mức sẵn sàng hiện tại.")
    add_table(doc, ["Hạng mục", "Lệnh kiểm tra", "Kết quả", "Trạng thái"], [
        ("Backend", "pytest -q tests", "72 đạt, 1 không đạt", "Cần xử lý"),
        ("Frontend unit/component", "npm test", "6 đạt, 4 không đạt", "Cần xử lý"),
        ("TypeScript", "npm run typecheck", "Không có lỗi kiểu", "Đạt"),
        ("Production build", "npm run build", "Build thành công 2661 module", "Đạt"),
    ], widths=[1.25, 1.8, 2.15, 1.25], font_size=9.0)
    heading(doc, "6.2.1 Phân tích lỗi kiểm thử", 3)
    add_table(doc, ["Vấn đề", "Bằng chứng", "Ảnh hưởng", "Hướng xử lý"], [
        ("Fixture gộp trùng backend", "Test mong ít nhất 1 tin trùng nhưng lượt chạy ghi nhận 9 tin mới, 0 trùng", "Một ca regression không ổn định", "Cố định dữ liệu fixture và khóa tiêu chí fingerprint/text similarity"),
        ("Trạng thái auth giữa test frontend", "4 test không tìm thấy nút admin sau khi chạy toàn bộ suite", "Component test phụ thuộc thứ tự", "Cleanup DOM, localStorage và mock auth trong afterEach; tạo test wrapper độc lập"),
    ], widths=[1.4, 2.1, 1.4, 1.6], font_size=8.6)

    heading(doc, "6.2.2 Ảnh chụp vận hành dữ liệu thật", 3)
    add_table(doc, ["Chỉ số", "Giá trị", "Nhận xét"], [
        ("Tin đang hoạt động", "247", "Dataset được đánh dấu live, seeded=false"),
        ("Cấu hình nguồn", "102", "101 nguồn đang bật; gồm HTML tĩnh, Playwright, API và nguồn nội bộ"),
        ("Lượt chạy crawler", "219", "50 success, 151 partial, 14 error, 4 running"),
        ("Pipeline run", "237", "Có lịch sử xử lý và theo dõi số lượng qua từng bước"),
        ("Tài khoản vận hành", "3", "Mỗi vai trò student, landlord, admin có một tài khoản"),
    ], widths=[1.7, 1.35, 3.15], font_size=9.2)
    add_body(doc, "Tỷ lệ lượt crawl thành công hoàn toàn còn thấp so với số lượt partial. Nguyên nhân thường gặp là selector thay đổi, trang chặn tự động hóa hoặc không trả dữ liệu phù hợp. Vì vậy, số lượng nguồn cấu hình không đồng nghĩa với số nguồn tạo dữ liệu ổn định; dashboard sức khỏe nguồn và quy trình duyệt selector cần tiếp tục được dùng như cổng kiểm soát vận hành.")

    heading(doc, "6.2.3 Đánh giá mức độ đáp ứng", 3)
    add_table(doc, ["Tiêu chí", "Hiện trạng", "Đánh giá"], [
        ("Đủ ba vai trò", "Có luồng sinh viên, chủ trọ và quản trị viên", "Đáp ứng"),
        ("Tìm kiếm AI có kiểm chứng", "LLM kết hợp schema, Pydantic, luật và fallback", "Đáp ứng thiết kế"),
        ("Bản đồ không cần API key", "Leaflet/OpenStreetMap và vị trí trình duyệt", "Đáp ứng"),
        ("Dữ liệu thật Đà Nẵng", "247 tin active, dataset live", "Đáp ứng ở quy mô thử nghiệm"),
        ("Thu thập đa nguồn ổn định", "Nhiều lượt partial/error", "Chưa đạt mức production"),
        ("Chất lượng kiểm thử", "Typecheck/build đạt nhưng còn 5 test thất bại", "Chưa đạt cổng phát hành"),
        ("Đo lường AI định lượng", "Có schema lưu AIUsage và cấu hình eval, chưa có bộ đánh giá độc lập hoàn chỉnh trong lần chạy này", "Cần bổ sung"),
    ], widths=[1.85, 3.05, 1.55], font_size=9.0)

    heading(doc, "6.2.4 Kiến nghị trước nghiệm thu", 3)
    add_bullets(doc, [
        "Sửa năm ca kiểm thử đang thất bại và đưa toàn bộ test vào một lệnh CI bắt buộc trước khi phát hành.",
        "Tách nguồn đang hoạt động ổn định khỏi nguồn chỉ mới được cấu hình; chỉ hiển thị dữ liệu từ lượt crawl có kết quả hợp lệ.",
        "Xây bộ dữ liệu gán nhãn riêng cho trích xuất, gộp trùng, rủi ro, giá và gợi ý; không dùng số liệu seed làm kết quả nghiên cứu.",
        "Theo dõi p95 latency, tỷ lệ lỗi API, tỷ lệ crawl thành công và chi phí AI theo ngày trong giai đoạn thử nghiệm.",
        "Chạy kiểm thử E2E trên Chrome ở kích thước desktop và mobile cho các luồng đăng nhập, tìm phòng, lưu tin, đăng phòng và quản trị nguồn.",
    ])

    heading(doc, "PHỤ LỤC CĂN CỨ KỸ THUẬT", 1)
    add_table(doc, ["Nội dung", "Tệp mã nguồn chính"], [
        ("Định tuyến và phân quyền frontend", "frontend/src/App.tsx, frontend/src/lib/auth.tsx"),
        ("REST client và kiểu dữ liệu", "frontend/src/lib/api.ts, frontend/src/lib/types.ts"),
        ("Mô hình cơ sở dữ liệu", "backend/app/models.py, backend/alembic/versions"),
        ("API nghiệp vụ", "backend/app/routes_public.py, routes_student.py, routes_landlord.py, routes_admin.py"),
        ("Tìm kiếm và AI", "backend/app/search.py, query_parser.py, extract.py, recommend.py, pricing.py, risk.py"),
        ("Thu thập và pipeline", "backend/app/worker.py, pipeline.py, crawler/phongoi_crawler"),
        ("Kiểm thử", "backend/tests, frontend/src/**/*.test.tsx, e2e/test_admin_smoke.py"),
        ("Triển khai", "docker-compose.yml, backend/Dockerfile, frontend/Dockerfile, frontend/nginx.conf"),
    ], widths=[2.2, 4.2], font_size=9.2)

    # Ask Word/LibreOffice to update fields such as TOC on open.
    settings = doc.settings._element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")

    props = doc.core_properties
    props.title = "Báo cáo phân tích thiết kế xây dựng và kiểm thử hệ thống Phòng Ơi"
    props.subject = "Hệ thống tìm phòng trọ AI cho sinh viên Đà Nẵng"
    props.author = "Nhóm 5 ST23D Trường Đại học Đông Á"
    props.keywords = "Phòng Ơi, AI, phòng trọ, FastAPI, React, Đà Nẵng"
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build_document()
