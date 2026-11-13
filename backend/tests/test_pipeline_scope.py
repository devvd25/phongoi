from app.pipeline import RawPost, is_danang_post


def post(source_name: str, text: str) -> RawPost:
    return RawPost(source_name=source_name, url="https://example.com/listing", text=text)


def test_accepts_post_with_danang_district():
    assert is_danang_post(post("Nguồn tổng hợp", "Cho thuê phòng trọ tại quận Hải Châu, giá 3 triệu đồng."))


def test_accepts_post_from_explicitly_danang_scoped_source():
    assert is_danang_post(post("Mogi Đà Nẵng", "Cho thuê studio đầy đủ nội thất, giá 4 triệu đồng."))


def test_rejects_explicit_out_of_scope_city_even_from_danang_source():
    assert not is_danang_post(post("Mogi Đà Nẵng", "Cho thuê phòng trọ Quận 1, TP Hồ Chí Minh, giá 4 triệu đồng."))

