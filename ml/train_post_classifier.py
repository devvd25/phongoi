"""Huấn luyện mô hình học máy (CPU) phân loại bài đăng Facebook Groups Phòng Trọ Đà Nẵng.

So sánh các thuật toán phân loại văn bản (LinearSVC, Logistic Regression, Random Forest)
trên đặc trưng TF-IDF n-grams để:
1. Phân loại ý định bài đăng (intent):
   - rental_offer: Tin cho thuê phòng / căn hộ / nhượng phòng
   - room_seeker : Tin người thuê / sinh viên đi tìm phòng
   - spam        : Tin quảng cáo dịch vụ chuyển trọ, lắp wifi, bình luận rác
2. Phân loại người đăng (poster_type):
   - owner       : Chính chủ hoặc sinh viên nhượng lại phòng lẻ
   - broker      : Môi giới / hệ thống căn hộ dịch vụ đăng nhiều phòng

Chạy từ thư mục backend:
    python ../ml/train_post_classifier.py
Mô hình tốt nhất được lưu vào backend/models/post_classifier.joblib (< 300 KB, chạy CPU < 1ms).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(ROOT))

import joblib  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.svm import LinearSVC  # noqa: E402

from app.catalog import norm  # noqa: E402

INTENT_CORPUS: list[tuple[str, str]] = [
    # --- RENTAL OFFERS (Tin cho thuê phòng / nhượng phòng Đà Nẵng) ---
    ("Cho thuê phòng trọ mới xây kiệt Hoàng Diệu, Hải Châu, Đà Nẵng. Giá 2tr8/tháng, diện tích 25m2, có gác lửng, máy lạnh, wc riêng, giờ giấc tự do.", "rental_offer"),
    ("Chính chủ còn 1 phòng trống đường Nguyễn Văn Linh, quận Hải Châu. Giá 2.5 triệu/tháng, rộng 22m2, có điều hòa, nóng lạnh, không chung chủ.", "rental_offer"),
    ("Pass lại phòng trọ gần ĐH Kinh Tế Đà Nẵng, đường Mỹ An, Ngũ Hành Sơn. Giá 2tr2/tháng, đầy đủ nội thất, vào ở ngay.", "rental_offer"),
    ("Nhượng lại hợp đồng phòng studio ban công thoáng mát tại Sơn Trà, Đà Nẵng. Giá thuê 3tr5/tháng, điện 3.5k, nước 50k/người.", "rental_offer"),
    ("Cho thuê căn hộ mini gần cầu Rồng, Sơn Trà, Đà Nẵng. Full nội thất máy giặt riêng, tủ lạnh, điều hòa, giá 4 triệu/tháng.", "rental_offer"),
    ("Cho thuê phòng trọ sinh viên đường Ngô Sĩ Liên, Hòa Khánh Bắc, Liên Chiểu gần ĐH Bách Khoa. Giá 1tr6/tháng, có gác lửng, wifi miễn phí.", "rental_offer"),
    ("ptr 2tr5 hc wifi ml kcc gtd vsr 22m2 đường Lê Duẩn Đà Nẵng liên hệ 0905123456", "rental_offer"),
    ("Cho thuê nhà nguyên căn 2 tầng kiệt Điện Biên Phủ, Thanh Khê, Đà Nẵng. 3 phòng ngủ, giá 6.5 triệu/tháng, phù hợp nhóm sinh viên.", "rental_offer"),
    ("Cần tìm 1 bạn nữ ở ghép phòng đã có sẵn tại đường Phan Châu Trinh, Hải Châu. Phòng rộng 28m2 đủ đồ, chia tiền phòng 1tr3/người.", "rental_offer"),
    ("Phòng trọ giá rẻ gần ĐH Sư Phạm và ĐH Bách Khoa Liên Chiểu, giá 1tr8/tháng, wc khép kín, chỗ để xe rộng có camera an ninh.", "rental_offer"),
    ("Cho thuê studio mới 100% đường Châu Thị Vĩnh Tế, Ngũ Hành Sơn gần ĐH Kinh Tế. Giá 3.2 triệu, nội thất cao cấp, thang máy, khóa vân tay.", "rental_offer"),
    ("Chính chủ cho thuê phòng trọ đường Nguyễn Tất Thành, Thanh Khê, Đà Nẵng. Diện tích 20m2, giá 2tr3, cọc 1 tháng, điện 3.5k.", "rental_offer"),
    ("Còn 2 phòng trống mới sơn sửa tại Khuê Trung, Cẩm Lệ gần ĐH Ngoại Ngữ. Giá 2 triệu/tháng, có máy lạnh, ban công phơi đồ riêng.", "rental_offer"),
    ("Cho thuê phòng ngủ khép kín trong nhà nguyên căn tại Hòa Xuân, Cẩm Lệ. Giá 2tr6/tháng, đầy đủ bếp, máy giặt, tủ lạnh dùng chung.", "rental_offer"),
    ("Góc pass phòng gấp tại kiệt Núi Thành, Hải Châu gần ĐH Đông Á và Kiến Trúc. Giá 2tr4/tháng, phòng có gác, máy lạnh, giảm 500k tháng đầu.", "rental_offer"),
    ("Hệ thống căn hộ dịch vụ cho thuê khắp Hải Châu, Sơn Trà, Ngũ Hành Sơn. Giá từ 3tr - 6tr/tháng, full nội thất.", "rental_offer"),
    ("Cho thuê phòng trọ đường Tôn Đức Thắng, Liên Chiểu. Giá 1.500.000đ/tháng, rộng 18m2, giờ giấc tự do, không chung chủ.", "rental_offer"),
    ("Phòng trọ mới tinh gần cầu Sông Hàn, giá 3 triệu/tháng, diện tích 26m2, cửa sổ lớn, máy nước nóng, điều hòa tiết kiệm điện.", "rental_offer"),
    # --- ROOM SEEKERS (Sinh viên / Người thuê đi tìm phòng) ---
    ("Mình là nữ sinh viên năm 2 ĐH Kinh Tế Đà Nẵng cần tìm phòng trọ khu vực Ngũ Hành Sơn hoặc Sơn Trà tài chính dưới 2tr5, ai có phòng trống chỉ giúp em với ạ!", "room_seeker"),
    ("Em là tân sinh viên ĐH Bách Khoa Đà Nẵng cần tìm phòng trọ khu vực Hòa Khánh, Liên Chiểu tài chính khoảng 2 triệu/tháng, có gác lửng. Anh chị nào biết chỉ giúp em!", "room_seeker"),
    ("Cần tìm phòng trọ cho 2 nam sinh viên ĐH Duy Tân khu vực Hải Châu hoặc Thanh Khê, giá quay đầu 2tr8, có máy lạnh và giờ giấc tự do.", "room_seeker"),
    ("Nữ nhân viên văn phòng cần thuê căn hộ mini hoặc studio khu vực Sơn Trà, Hải Châu tài chính 3tr - 3tr5, yêu cầu sạch sẽ an ninh, ai có ib mình nhé.", "room_seeker"),
    ("Mình cần tìm 1 phòng trọ gần ĐH Đông Á hoặc ĐH Kiến Trúc, tài chính dưới 2 triệu, có wc riêng, dọn vào đầu tháng sau. Xin cảm ơn!", "room_seeker"),
    ("Tìm phòng trọ quanh khu vực cầu Rồng hoặc Nguyễn Văn Linh giá dưới 3 triệu, ưu tiên chính chủ không qua môi giới, ai có phòng cho mình xin ảnh và giá ạ.", "room_seeker"),
    ("2 nữ sinh viên ĐH Sư Phạm cần tìm phòng trọ đường Tôn Đức Thắng hoặc Ngô Sĩ Liên, giá tầm 1tr5 - 2tr, anh chị chủ trọ nào còn phòng ib em với ạ.", "room_seeker"),
    ("Cần tìm người ở ghép hoặc tìm phòng nhỏ dưới 1tr8 khu vực Thanh Khê, mình hiền lành gọn gàng chưa có phòng sẵn muốn tìm bạn cùng đi thuê.", "room_seeker"),
    ("Gia đình nhỏ cần thuê nhà nguyên căn hoặc căn hộ 2 phòng ngủ tại Cẩm Lệ hoặc Hòa Xuân, tài chính 5 triệu quay đầu, ai biết giới thiệu giúp mình.", "room_seeker"),
    ("Có anh chị nào pass phòng khu vực Bắc Mỹ An gần ĐH Kinh Tế giá tầm 2tr - 2tr5 không ạ? Em đang cần tìm phòng gấp trong tuần này.", "room_seeker"),
    ("Sinh viên FPT cần tìm phòng trọ khu vực Hòa Hải, Ngũ Hành Sơn, tài chính 2 triệu, có điều hòa, ai còn phòng trống cmt giúp em nhé.", "room_seeker"),
    ("Mình cần tìm trọ gần bệnh viện Đà Nẵng quận Hải Châu, giá khoảng 2tr5 đổ lại, không ngập nước, giờ tự do. Ai có phòng ib giúp mình.", "room_seeker"),
    # --- SPAM / IRRELEVANT (Quảng cáo dịch vụ chuyển trọ, wifi, bình luận rác) ---
    ("Dịch vụ xe tải chuyển nhà, chuyển phòng trọ sinh viên giá rẻ toàn Đà Nẵng. Có đội bốc xếp nhiệt tình, gọi ngay 0905999888.", "spam"),
    ("Nhận lắp đặt mạng internet wifi Viettel, FPT, VNPT cho phòng trọ sinh viên tại Đà Nẵng. Miễn phí hòa mạng, tặng thêm tháng cước, ib ngay.", "spam"),
    ("Chuyên vệ sinh máy lạnh, sửa chữa tủ lạnh, máy giặt, bình nóng lạnh tại nhà khu vực Đà Nẵng giá sinh viên. Liên hệ 0912333444.", "spam"),
    ("ib mình nhé check inbox bạn ơi chấm bài cho đỡ trôi .", "spam"),
    ("Thanh lý tủ lạnh mini, quạt điện, bàn học, nệm sinh viên giá rẻ tại Hòa Khánh, Liên Chiểu. Bạn nào cần mua đồ dùng phòng trọ inbox mình.", "spam"),
    ("Tuyển nhân viên phục vụ quán cafe ca tối tại Hải Châu, Đà Nẵng, lương 22k/giờ, bao ăn tối, liên hệ quản lý.", "spam"),
    ("Cho vay tiền mặt hỗ trợ tài chính sinh viên Đà Nẵng giải ngân nhanh trong ngày chỉ cần CCCD.", "spam"),
    ("Xin giá ạ, check ib giúp em với shop ơi, chấm hóng.", "spam"),
    ("Nhận chở hàng xe ba gác, xe tải nhỏ chuyển trọ sinh viên Bách Khoa, Kinh Tế, Duy Tân giá chỉ từ 150k/chuyến.", "spam"),
    ("Bán sim data 4G Viettel Mobi Vina dung lượng khủng cho sinh viên ở trọ không cần kéo wifi.", "spam"),
]

BROKER_CORPUS: list[tuple[str, str]] = [
    # --- OWNER (Chính chủ / Sinh viên pass phòng đơn lẻ) ---
    ("Chính chủ cho thuê 1 phòng trọ trống tại kiệt 120 Hoàng Diệu, Hải Châu. Giá 2tr6/tháng, diện tích 22m2, không qua trung gian.", "owner"),
    ("Mình ra trường nên cần pass lại phòng trọ đang ở gần ĐH Kinh Tế, giá 2tr2/tháng, chủ nhà cô chú cực kỳ dễ tính.", "owner"),
    ("Nhà mình còn dư 1 phòng trên tầng 2 đường Lê Độ, Thanh Khê muốn cho nữ sinh viên hoặc người đi làm thuê lâu dài, giá 1tr8.", "owner"),
    ("Góc nhượng phòng chính chủ: Do chuyển công tác nên mình nhượng lại studio tại Sơn Trà giá 3tr2, tặng lại nửa tháng tiền phòng.", "owner"),
    ("Cần tìm 1 bạn nữ ở ghép vào phòng mình đang thuê tại đường Nguyễn Văn Thoại, phòng có sẵn tủ lạnh máy giặt, chia tiền 1tr4/tháng.", "owner"),
    ("Gia đình còn 2 phòng trọ mới xây tại Hòa Khánh Bắc gần ĐH Bách Khoa, giá 1tr7/tháng, điện nước theo giá nhà nước, chính chủ đăng tin.", "owner"),
    # --- BROKER (Môi giới / Hệ thống căn hộ / Sale dẫn khách) ---
    ("Hệ thống căn hộ mini & studio cho thuê khắp Hải Châu, Sơn Trà, Ngũ Hành Sơn. Nhiều mức giá chỉ từ 3tr - 6tr/tháng, giỏ hàng hơn 50 phòng trống, hỗ trợ tìm phòng miễn phí, inbox gửi video thực tế.", "broker"),
    ("Tổng hợp quỹ phòng trọ & căn hộ giá rẻ toàn Đà Nẵng cập nhật mỗi ngày. Đa dạng phân khúc từ 2tr5 - 7tr, cam kết hỗ trợ dẫn xem phòng miễn phí 100%, liên hệ zalo sale.", "broker"),
    ("Bên mình đang quản lý hơn 30 tòa căn hộ dịch vụ tại Sơn Trà và Hải Châu, luôn có sẵn phòng studio, 1PN, 2PN, nhận ký gửi và dẫn khách hoa hồng cao.", "broker"),
    ("List phòng trọ sinh viên trống tháng này quanh ĐH Kinh Tế, Duy Tân, Đông Á: 1. Phòng 2tr2 Mỹ An, 2. Studio 3tr2 Châu Thị Vĩnh Tế, 3. Căn hộ 4tr Phan Tứ. Inbox mình gửi hình từng căn và dẫn đi xem miễn phí.", "broker"),
    ("Chuyên cho thuê chuỗi căn hộ mini cao cấp tại Đà Nẵng, hỗ trợ tìm phòng theo yêu cầu ngân sách từ 2tr5 đến 10tr, inbox zalo để nhận báo giá và video 20 căn đang trống.", "broker"),
    ("Tuyển cộng tác viên sale phòng trọ và căn hộ Đà Nẵng, giỏ hàng hơn 500 căn toàn thành phố, hoa hồng 50-80% thanh toán ngay khi chốt cọc.", "broker"),
]


def train_and_save(out_path: Path | None = None) -> dict:
    # Nhân bản dữ liệu với biến thể chuẩn hóa không dấu để mô hình học tốt cả có dấu và không dấu
    X_intent, y_intent = [], []
    for text, label in INTENT_CORPUS:
        X_intent.append(text.lower())
        y_intent.append(label)
        X_intent.append(norm(text))
        y_intent.append(label)

    Xtr, Xte, ytr, yte = train_test_split(X_intent, y_intent, test_size=0.2, random_state=42, stratify=y_intent)

    candidates = {
        "LinearSVC (Calibrated)": CalibratedClassifierCV(LinearSVC(C=1.5, random_state=42), cv=3),
        "Logistic Regression": LogisticRegression(C=2.0, max_iter=500, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=150, random_state=42),
    }

    best_name, best_pipe, best_f1 = "", None, -1.0
    metrics = {}
    for name, clf in candidates.items():
        pipe = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1),
            clf,
        )
        pipe.fit(Xtr, ytr)
        preds = pipe.predict(Xte)
        acc = accuracy_score(yte, preds)
        f1 = f1_score(yte, preds, average="macro")
        metrics[name] = {"accuracy": round(float(acc), 4), "f1_macro": round(float(f1), 4)}
        if f1 > best_f1:
            best_f1 = f1
            best_name = name
            # Refit on full corpus for production deployment
            best_pipe = make_pipeline(
                TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1),
                clf,
            ).fit(X_intent, y_intent)

    X_broker, y_broker = [], []
    for text, label in BROKER_CORPUS:
        X_broker.append(text.lower())
        y_broker.append(label)
        X_broker.append(norm(text))
        y_broker.append(label)

    broker_pipe = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1),
        CalibratedClassifierCV(LinearSVC(C=1.5, random_state=42), cv=3),
    ).fit(X_broker, y_broker)

    bundle = {
        "model_name": best_name,
        "intent_pipe": best_pipe,
        "broker_pipe": broker_pipe,
        "metrics": metrics,
    }

    target = out_path or (ROOT / "models" / "post_classifier.joblib")
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, target)
    return bundle


def main() -> None:
    bundle = train_and_save()
    print(f"{'Mô hình phân loại':<26}{'Accuracy':>12}{'F1-Macro':>12}")
    for name, m in bundle["metrics"].items():
        print(f"{name:<26}{m['accuracy'] * 100:>11.1f}%{m['f1_macro']:>12.3f}")
    print(f"\nĐã lưu mô hình tốt nhất ({bundle['model_name']}) -> {ROOT / 'models' / 'post_classifier.joblib'}")


if __name__ == "__main__":
    main()

