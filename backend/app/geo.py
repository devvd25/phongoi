"""Tính khoảng cách Haversine và nội suy tọa độ thực tế theo Đường/Phường/Quận tại Đà Nẵng."""

import hashlib
import math
import re

from .catalog import DISTRICTS, norm

# Tọa độ thực tế (lat, lng) của các tuyến đường và phường trọng điểm sinh viên tại Đà Nẵng
LOCATION_COORDS: dict[str, tuple[float, float]] = {
    # Liên Chiểu
    "ngô sĩ liên": (16.0748, 108.1528),
    "nguyễn lương bằng": (16.0765, 108.1482),
    "phạm như xương": (16.0642, 108.1558),
    "ngô thì nhậm": (16.0695, 108.1562),
    "âu cơ": (16.0680, 108.1425),
    "tôn đức thắng": (16.0625, 108.1635),
    "hoàng văn thái": (16.0545, 108.1480),
    "nguyễn văn cừ": (16.1180, 108.1225),
    "mê linh": (16.1085, 108.1260),
    "lạc long quân": (16.0825, 108.1450),
    "nguyễn chánh": (16.0785, 108.1595),
    "hoàng thị loan": (16.0595, 108.1695),
    "kinh dương vương": (16.0725, 108.1685),
    "nguyễn sinh sắc": (16.0755, 108.1645),
    "nam cao": (16.0660, 108.1390),
    "hòa khánh bắc": (16.0755, 108.1495),
    "hòa khánh nam": (16.0615, 108.1545),
    "hòa minh": (16.0620, 108.1680),
    "hòa hiệp nam": (16.1050, 108.1310),
    "hòa khánh": (16.0720, 108.1520),
    # Thanh Khê
    "mẹ nhu": (16.0638, 108.1795),
    "hà huy tập": (16.0668, 108.1855),
    "điện biên phủ": (16.0658, 108.1920),
    "lê độ": (16.0692, 108.1985),
    "trần cao vân": (16.0718, 108.1960),
    "hàm nghi": (16.0612, 108.2095),
    "nguyễn tri phương": (16.0558, 108.2015),
    "lê trọng tấn": (16.0510, 108.1810),
    "thái thị bôi": (16.0680, 108.1910),
    "cù chính lan": (16.0645, 108.1830),
    "huỳnh ngọc huệ": (16.0615, 108.1870),
    "nguyễn phước nguyên": (16.0590, 108.1865),
    "nguyễn tất thành": (16.0760, 108.1850),
    "thanh khê tây": (16.0665, 108.1785),
    "thanh khê đông": (16.0690, 108.1850),
    "an khê": (16.0575, 108.1845),
    "hòa khê": (16.0615, 108.1885),
    "thạc gián": (16.0625, 108.2085),
    "vĩnh trung": (16.0645, 108.2110),
    # Hải Châu
    "lê đình lý": (16.0545, 108.2095),
    "ông ích khiêm": (16.0675, 108.2145),
    "nguyễn văn linh": (16.0605, 108.2165),
    "hoàng diệu": (16.0585, 108.2185),
    "núi thành": (16.0425, 108.2215),
    "xô viết nghệ tĩnh": (16.0345, 108.2195),
    "trưng nữ vương": (16.0495, 108.2175),
    "phan châu trinh": (16.0635, 108.2210),
    "lê duẩn": (16.0705, 108.2180),
    "quang trung": (16.0755, 108.2185),
    "đống đa": (16.0785, 108.2175),
    "3 tháng 2": (16.0845, 108.2175),
    "2 tháng 9": (16.0455, 108.2245),
    "30 tháng 4": (16.0365, 108.2165),
    "tiểu la": (16.0435, 108.2165),
    "nguyễn hữu thọ": (16.0445, 108.2085),
    "lê thanh nghị": (16.0385, 108.2165),
    "phan đăng lưu": (16.0395, 108.2195),
    "hòa cường bắc": (16.0415, 108.2190),
    "hòa cường nam": (16.0335, 108.2195),
    "hòa thuận tây": (16.0515, 108.2065),
    "hòa thuận đông": (16.0535, 108.2145),
    "bình hiên": (16.0565, 108.2215),
    "bình thuận": (16.0525, 108.2195),
    "thạch thang": (16.0765, 108.2205),
    "hải châu 1": (16.0695, 108.2225),
    "hải châu 2": (16.0675, 108.2175),
    # Sơn Trà
    "ngô quyền": (16.0725, 108.2345),
    "phạm văn đồng": (16.0705, 108.2395),
    "lê hữu trác": (16.0625, 108.2395),
    "hồ nghinh": (16.0685, 108.2435),
    "võ nguyên giáp": (16.0665, 108.2465),
    "võ văn kiệt": (16.0615, 108.2385),
    "nguyễn văn thoại": (16.0545, 108.2415),
    "trần hưng đạo": (16.0695, 108.2295),
    "khúc hạo": (16.0855, 108.2375),
    "dương đình nghệ": (16.0695, 108.2415),
    "vương thừa vũ": (16.0735, 108.2435),
    "an hải bắc": (16.0735, 108.2355),
    "an hải đông": (16.0585, 108.2395),
    "an hải tây": (16.0625, 108.2325),
    "phước mỹ": (16.0645, 108.2435),
    "mân thái": (16.0825, 108.2445),
    "nại hiên đông": (16.0895, 108.2315),
    "thọ quang": (16.0965, 108.2415),
    # Ngũ Hành Sơn
    "trà khê 8": (15.9865, 108.2585),
    "trà khê": (15.9870, 108.2580),
    "lê văn hiến": (16.0185, 108.2495),
    "ngũ hành sơn": (16.0425, 108.2405),
    "trần đại nghĩa": (15.9785, 108.2565),
    "mai đăng chơn": (15.9925, 108.2445),
    "châu thị vĩnh tế": (16.0465, 108.2425),
    "bà huyện thanh quan": (16.0435, 108.2445),
    "đỗ bá": (16.0485, 108.2455),
    "phan tứ": (16.0445, 108.2455),
    "an thượng 1": (16.0505, 108.2455),
    "an thượng 2": (16.0500, 108.2460),
    "an thượng 3": (16.0495, 108.2465),
    "an thượng 4": (16.0490, 108.2470),
    "an thượng": (16.0500, 108.2460),
    "hoàng kế viêm": (16.0510, 108.2465),
    "chương dương": (16.0385, 108.2365),
    "nam kỳ khởi nghĩa": (15.9755, 108.2525),
    "mỹ an": (16.0455, 108.2445),
    "bắc mỹ an": (16.0425, 108.2440),
    "khuê mỹ": (16.0265, 108.2465),
    "hòa hải": (15.9925, 108.2585),
    "hòa quý": (15.9855, 108.2395),
    # Cẩm Lệ
    "lỗ giáng 8": (16.0085, 108.2185),
    "lỗ giáng": (16.0090, 108.2180),
    "cách mạng tháng tám": (16.0265, 108.2095),
    "ông ích đường": (16.0215, 108.2015),
    "lương nhữ hộc": (16.0315, 108.2125),
    "trường chinh": (16.0355, 108.1855),
    "thăng long": (16.0245, 108.2165),
    "phạm hùng": (16.0025, 108.2095),
    "võ an ninh": (16.0125, 108.2165),
    "đô đốc lân": (16.0145, 108.2195),
    "nguyễn phước lan": (16.0155, 108.2215),
    "cồn dầu": (16.0115, 108.2245),
    "tôn đản": (16.0485, 108.1835),
    "lê đại hành": (16.0295, 108.2055),
    "khuê trung": (16.0285, 108.2095),
    "hòa xuân": (16.0115, 108.2185),
    "nam hòa xuân": (16.0015, 108.2285),
    "hòa an": (16.0465, 108.1815),
    "hòa phát": (16.0365, 108.1795),
    "hòa thọ đông": (16.0165, 108.1965),
    "hòa thọ tây": (16.0115, 108.1815),
}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def approx_location(district: str | None, address: str) -> tuple[float, float]:
    """Tọa độ chuẩn xác theo tuyến đường / phường tại Đà Nẵng + độ lệch nhỏ cố định theo số nhà/địa chỉ."""
    # Bỏ phần hậu tố Quận/Thành phố ở cuối chuỗi địa chỉ để ưu tiên khớp đúng Đường/Phường ở đầu địa chỉ
    raw_head = re.sub(r",\s*(?:Liên Chiểu|Thanh Khê|Hải Châu|Sơn Trà|Ngũ Hành Sơn|Cẩm Lệ|Hòa Vang)?\s*,?\s*Đà Nẵng\s*$", "", address or "", flags=re.I)
    n_addr = norm(raw_head or address or "")
    matched_coord: tuple[float, float] | None = None
    best_pos = 10**9
    best_len = 0

    for key, coord in LOCATION_COORDS.items():
        nk = norm(key)
        if m := re.search(rf"(?<![a-z0-9]){re.escape(nk)}(?![a-z0-9])", n_addr):
            if m.start() < best_pos or (m.start() == best_pos and len(nk) > best_len):
                best_pos = m.start()
                best_len = len(nk)
                matched_coord = coord

    h = hashlib.md5((address or district or "Đà Nẵng").encode()).digest()
    if matched_coord is not None:
        base_lat, base_lng = matched_coord
        # Độ lệch nhỏ ±120m quanh tâm tuyến đường/phường để các pin cùng đường không đè hoàn toàn lên nhau
        dlat = (h[0] / 255 - 0.5) * 0.0022
        dlng = (h[1] / 255 - 0.5) * 0.0022
        return round(base_lat + dlat, 6), round(base_lng + dlng, 6)

    c = DISTRICTS.get(district or "", DISTRICTS["Hải Châu"])
    dlat = (h[0] / 255 - 0.5) * 0.009
    dlng = (h[1] / 255 - 0.5) * 0.009
    return round(c["lat"] + dlat, 6), round(c["lng"] + dlng, 6)


def travel_text(km: float) -> str:
    if km <= 1.0:
        return f"{km:.1f} km · {max(1, round(km / 5 * 60))} phút đi bộ".replace(".", ",")
    return f"{km:.1f} km · {max(2, round(km / 25 * 60))} phút xe máy".replace(".", ",")
