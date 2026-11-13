"""Bộ phân loại bài đăng Facebook Phòng Trọ Đà Nẵng chạy trên CPU (< 1ms, 0% GPU).

Sử dụng mô hình học máy TF-IDF + LinearSVC/LogisticRegression (`models/post_classifier.joblib`)
kết hợp tập luật ngữ nghĩa tiếng Việt Đà Nẵng để:
1. Phân loại bài đăng thành:
   - `rental_offer`: Tin cho thuê phòng, căn hộ, nhượng phòng, tìm người vào ở ghép phòng đã có sẵn.
   - `room_seeker` : Tin sinh viên/người thuê đi tìm phòng (cần loại bỏ trước khi trích xuất).
   - `spam`        : Tin quảng cáo dịch vụ chuyển trọ, lắp mạng, bình luận rác ("ib", "chấm").
2. Nhận diện người đăng:
   - `owner`       : Chính chủ hoặc sinh viên nhượng lại phòng lẻ.
   - `broker`      : Môi giới / hệ thống căn hộ dịch vụ đăng nhiều phòng.
"""

import os
import re
from pathlib import Path

import joblib

from .catalog import norm

_BUNDLE: dict = {"loaded": False, "data": None}

# Các mẫu câu đặc trưng của người đi tìm phòng (Seeker)
SEEKER_PATTERNS = (
    r"\b(?:can\s+tim\s+phong|tim\s+phong\s+tro|can\s+thue\s+phong|can\s+thue\s+can\s+ho|can\s+tim\s+tro)\b",
    r"\b(?:tai\s+chinh\s+(?:duoi|khoang|tam|tu)|gia\s+quay\s+dau)\b",
    r"\b(?:ai\s+co\s+phong\s+trong|chi\s+giup\s+em|anh\s+chi\s+nao\s+biet\s+chi\s+giup|co\s+ai\s+pass\s+phong)\b",
)

# Các mẫu câu xác nhận người đăng ĐÃ CÓ PHÒNG (Offer)
OFFER_OVERRIDE_PATTERNS = (
    r"\b(?:cho\s+thue|con\s+\d+\s+phong\s+trong|chinh\s+chu\s+cho\s+thue|pass\s+lai\s+phong|nhuong\s+lai\s+phong|nhuong\s+lai\s+hop\s+dong|goc\s+pass\s+phong|phong\s+da\s+co\s+san|ptr\s+\d)\b",
)

# Các mẫu câu spam / dịch vụ ngoài luồng / bình luận rác
SPAM_PATTERNS = (
    r"^(?:ib|inbox|check\s*ib|cham|\.|hong|up|xin\s*gia|gia\s*sao)(?:\s+.*)?$",
    r"\b(?:xe\s+tai\s+chuyen\s+nha|chuyen\s+phong\s+tro\s+sinh\s+vien\s+gia\s+re|lap\s+dat\s+(?:mang|wifi)|ve\s+sinh\s+may\s+lanh|cho\s+vay\s+tien|thanh\s+ly\s+tu\s+lanh)\b",
)

# Các mẫu câu đặc trưng của môi giới / hệ thống căn hộ
BROKER_PATTERNS = (
    r"\b(?:he\s+thong\s+can\s+ho|gio\s+hang\s+hon|nhieu\s+muc\s+gia|ho\s+tro\s+tim\s+phong\s+mien\s+phi|inbox\s+gui\s+video|hoa\s+hong|tuyen\s+cong\s+tac\s+vien\s+sale|chuoi\s+can\s+ho)\b",
)


def _model_path() -> Path:
    return Path(__file__).resolve().parents[1] / "models" / "post_classifier.joblib"


def _load_bundle() -> dict | None:
    if not _BUNDLE["loaded"]:
        _BUNDLE["loaded"] = True
        p = _model_path()
        if not p.exists():
            try:
                ml_dir = Path(__file__).resolve().parents[2] / "ml"
                import sys

                if str(ml_dir) not in sys.path:
                    sys.path.insert(0, str(ml_dir))
                from train_post_classifier import train_and_save

                _BUNDLE["data"] = train_and_save(p)
                return _BUNDLE["data"]
            except Exception:
                return None
        if os.path.exists(p):
            try:
                _BUNDLE["data"] = joblib.load(p)
            except Exception:
                _BUNDLE["data"] = None
    return _BUNDLE["data"]


def classify_post(text: str) -> dict:
    """Phân loại nhanh bài đăng Facebook bằng mô hình ML trên CPU kết hợp luật kiểm chứng."""
    clean = (text or "").strip()
    n = norm(clean)

    if len(n) < 10 or any(re.search(pat, n) for pat in SPAM_PATTERNS):
        return {
            "intent": "spam",
            "is_rental": False,
            "poster_type": "owner",
            "is_broker": False,
            "confidence": 0.99,
            "engine": "ml_cpu",
        }

    has_offer_signal = any(re.search(pat, n) for pat in OFFER_OVERRIDE_PATTERNS)
    has_seeker_signal = any(re.search(pat, n) for pat in SEEKER_PATTERNS)
    has_broker_signal = any(re.search(pat, n) for pat in BROKER_PATTERNS)

    bundle = _load_bundle()
    ml_intent = "rental_offer"
    ml_conf = 0.85
    ml_poster = "owner"

    if bundle and bundle.get("intent_pipe") is not None:
        intent_pipe = bundle["intent_pipe"]
        probs = intent_pipe.predict_proba([n])[0]
        classes = list(intent_pipe.classes_)
        best_idx = int(probs.argmax())
        ml_intent = str(classes[best_idx])
        ml_conf = round(float(probs[best_idx]), 3)

        if bundle.get("broker_pipe") is not None:
            ml_poster = str(bundle["broker_pipe"].predict([n])[0])

    # Kết hợp dự đoán ML và tín hiệu ngữ nghĩa tiếng Việt Đà Nẵng
    if has_seeker_signal and not has_offer_signal:
        intent = "room_seeker"
    elif has_offer_signal:
        intent = "rental_offer"
    else:
        intent = ml_intent

    if has_broker_signal:
        poster_type = "broker"
    elif "chinh chu" in n or "pass lai phong" in n or "nhuong lai" in n:
        poster_type = "owner"
    else:
        poster_type = ml_poster

    return {
        "intent": intent,
        "is_rental": intent == "rental_offer",
        "poster_type": poster_type,
        "is_broker": poster_type == "broker",
        "confidence": ml_conf,
        "engine": "ml_cpu",
    }

