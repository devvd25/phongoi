"""Huấn luyện mô hình dự đoán giá thuê hợp lý (TransformedTargetRegressor Log-Price) và lưu metadata đánh giá.

Chạy từ thư mục backend:
    python ../ml/train_price_model.py
Mô hình tốt nhất được lưu vào backend/models/price_model.joblib, API /market/estimate và /listings/{id} tự dùng khi có file.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(ROOT))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.compose import TransformedTargetRegressor  # noqa: E402
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor  # noqa: E402
from sklearn.feature_extraction import DictVectorizer  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.geo import haversine_km  # noqa: E402
from app.models import Listing, School  # noqa: E402
from app.pricing import APARTMENT_TYPES, features  # noqa: E402


def main() -> None:
    db = SessionLocal()
    rows = db.query(Listing).filter(Listing.status != "hidden", Listing.risk_level != "high").all()
    schools = db.query(School).all()
    db.close()

    X = []
    y_list = []
    for l in rows:
        min_km = (
            min((haversine_km(l.lat, l.lng, s.lat, s.lng) for s in schools), default=1.5)
            if l.lat and l.lng
            else 1.5
        )
        is_apt = l.room_type in APARTMENT_TYPES or l.price > 5_500_000
        X.append(
            features(
                l.district,
                l.area,
                l.amenities or [],
                l.room_type,
                lat=l.lat,
                lng=l.lng,
                min_school_km=min_km,
                is_high_tier=is_apt,
            )
        )
        y_list.append(float(l.price))

    y = np.array(y_list, dtype=float)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

    candidates = {
        "Ridge Regression (Log)": TransformedTargetRegressor(
            regressor=Ridge(alpha=1.0), func=np.log1p, inverse_func=np.expm1
        ),
        "Random Forest (Log)": TransformedTargetRegressor(
            regressor=RandomForestRegressor(n_estimators=300, max_depth=12, random_state=42),
            func=np.log1p,
            inverse_func=np.expm1,
        ),
        "Gradient Boosting (Log)": TransformedTargetRegressor(
            regressor=GradientBoostingRegressor(n_estimators=250, max_depth=4, learning_rate=0.05, random_state=42),
            func=np.log1p,
            inverse_func=np.expm1,
        ),
    }

    best, best_mae = None, float("inf")
    print(f"{'Mô hình':<26}{'MAE (đ)':>12}{'MAPE':>9}{'R²':>8}")
    for name, model in candidates.items():
        pipe = make_pipeline(DictVectorizer(sparse=False), model).fit(Xtr, ytr)
        pred = pipe.predict(Xte)
        mae = mean_absolute_error(yte, pred)
        mape = mean_absolute_percentage_error(yte, pred) * 100
        r2 = r2_score(yte, pred)
        print(f"{name:<26}{mae:>12,.0f}{mape:>8.1f}%{r2:>8.2f}")
        if mae < best_mae:
            pipe.model_meta_ = {
                "name": name,
                "mae": int(round(mae)),
                "mape": round(float(mape), 1),
                "r2": round(float(r2), 2),
                "samples": len(rows),
            }
            best, best_mae = (name, pipe), mae

    out = ROOT / "models" / "price_model.joblib"
    out.parent.mkdir(exist_ok=True)
    joblib.dump(best[1], out)
    print(f"\nĐã lưu mô hình tốt nhất: {best[0]} -> {out}")
    print("Metadata:", best[1].model_meta_)


if __name__ == "__main__":
    main()
