from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .catalog import AMENITY_KEYS, DISTRICTS, ROOM_TYPES
from .db import get_db, utcnow
from .models import Listing, NeedsProfile, Notification, RecommendationFeedback, Report, SavedListing, School, User
from .money import short_vnd
from .notify import DEFAULT_PREFS, notify_admins, notify_savers, prefs_of
from .pricing import district_stats, monthly_cost
from .query_parser import SearchFilters, chips
from .recommend import match
from .risk import apply as apply_risk
from .routes_public import filters_from_profile, user_out
from .search import index_listing, run_search
from .security import current_user, current_user_optional
from .serializers import card

router = APIRouter(prefix="/api")


# ---------- Needs profile ----------
class NeedsIn(BaseModel):
    budget_min: int | None = Field(None, ge=0)
    budget_max: int | None = Field(None, ge=0)
    school_id: int | None = None
    max_distance_km: float | None = Field(None, gt=0, le=50)
    districts: list[str] = []
    room_types: list[str] = []
    amenities: list[str] = []
    max_people: int | None = Field(None, ge=1, le=10)
    transport: Literal["di_bo", "xe_dap", "xe_may", "xe_buyt"] = "xe_may"
    move_in: str | None = None


def needs_out(p: NeedsProfile | None, db: Session) -> dict | None:
    if not p:
        return None
    f = filters_from_profile(p)
    return {
        "budget_min": p.budget_min,
        "budget_max": p.budget_max,
        "school_id": p.school_id,
        "max_distance_km": p.max_distance_km,
        "districts": p.districts,
        "room_types": p.room_types,
        "amenities": p.amenities,
        "max_people": p.max_people,
        "transport": p.transport,
        "move_in": p.move_in,
        "chips": chips(f, db.query(School).all()) + ([f"Nhập học {p.move_in}"] if p.move_in else []),
    }


@router.get("/me/needs")
def get_needs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return needs_out(db.get(NeedsProfile, user.id), db)


@router.put("/me/needs")
def put_needs(body: NeedsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(NeedsProfile, user.id) or NeedsProfile(user_id=user.id)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    p.districts = [d for d in body.districts if d in DISTRICTS]
    p.amenities = [a for a in body.amenities if a in AMENITY_KEYS]
    p.room_types = [r for r in body.room_types if r in ROOM_TYPES]
    p.updated_at = utcnow()
    db.add(p)
    if body.school_id:
        user.school_id = body.school_id
    db.commit()
    return needs_out(p, db)


# ---------- Recommendations ----------
@router.get("/recommendations")
def recommendations(
    tab: Literal["match", "new", "cheap", "near"] = "match", user: User = Depends(current_user), db: Session = Depends(get_db)
):
    p = db.get(NeedsProfile, user.id)
    f = filters_from_profile(p)
    f.sort = {"match": "match", "new": "newest", "cheap": "price_asc", "near": "distance"}[tab]
    # Gợi ý nới ngân sách 10% để không bỏ sót phòng vừa vượt nhẹ.
    relaxed = f.model_copy(update={"budget_max": int(f.budget_max * 1.1) if f.budget_max else None})
    disliked = {fb.listing_id for fb in db.query(RecommendationFeedback).filter_by(user_id=user.id).all() if fb.listing_id}
    res = run_search(db, relaxed, page_size=13)
    items = [i for i in res["items"] if i["id"] not in disliked]
    top = items[0] if items else None
    return {
        "profile": needs_out(p, db),
        "total": res["total"],
        "top_pick": top,
        "items": items[1:9],
        "updated_at": utcnow().replace(hour=1, minute=0, second=0).isoformat() + "Z",
    }


class FeedbackIn(BaseModel):
    reason: Literal["too_far", "too_expensive", "room_type", "unsafe_area", "not_interested"]
    listing_id: int | None = None


@router.post("/recommendations/feedback")
def recommendation_feedback(body: FeedbackIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(RecommendationFeedback(user_id=user.id, listing_id=body.listing_id, reason=body.reason))
    p = db.get(NeedsProfile, user.id)
    if p:
        # Điều chỉnh hồ sơ nhẹ theo phản hồi để lần gợi ý sau sát hơn.
        if body.reason == "too_far" and p.max_distance_km:
            p.max_distance_km = max(1.0, round(p.max_distance_km * 0.8, 1))
        if body.reason == "too_expensive" and p.budget_max:
            p.budget_max = int(p.budget_max * 0.92)
    db.commit()
    return {"ok": True}


# ---------- Saved & compare ----------
@router.get("/me/saved")
def saved_list(user: User = Depends(current_user), db: Session = Depends(get_db)):
    stats = district_stats(db)
    rows = db.query(SavedListing, Listing).join(Listing, Listing.id == SavedListing.listing_id).filter(SavedListing.user_id == user.id).all()
    out = []
    for s, l in rows:
        diff = l.price - s.price_at_save
        if l.risk_level == "high":
            status = {"label": "Bị báo cáo", "tone": "Danger"}
        elif diff < 0:
            status = {"label": f"Giảm {short_vnd(-diff)}", "tone": "Success"}
        elif l.status == "rented":
            status = {"label": "Đã cho thuê", "tone": "Neutral"}
        else:
            status = {"label": "Giá không đổi", "tone": "Neutral"}
        out.append({**card(l, None, stats), "status_badge": status, "contacted": s.contacted, "saved_at": s.created_at.isoformat() + "Z"})
    return out


@router.post("/me/saved/{listing_id}")
def save(listing_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    l = db.get(Listing, listing_id)
    if not l:
        raise HTTPException(404, "Không tìm thấy tin đăng")
    if not db.get(SavedListing, (user.id, listing_id)):
        db.add(SavedListing(user_id=user.id, listing_id=listing_id, price_at_save=l.price))
        l.saves += 1
        db.commit()
    return {"saved": True}


@router.delete("/me/saved/{listing_id}")
def unsave(listing_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(SavedListing, (user.id, listing_id))
    if s:
        db.delete(s)
        db.commit()
    return {"saved": False}


@router.get("/me/compare")
def compare(ids: str = Query(..., description="Danh sách id, cách nhau bởi dấu phẩy"), user: User = Depends(current_user), db: Session = Depends(get_db)):
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()][:4]
    stats = district_stats(db)
    p = db.get(NeedsProfile, user.id)
    f = filters_from_profile(p)
    school = db.get(School, f.school_id) if f.school_id else None
    cols = []
    for lid in id_list:
        l = db.get(Listing, lid)
        if not l:
            continue
        m = match(l, f, school, stats)
        cols.append(
            {
                "id": l.id,
                "title": l.title,
                "price": l.price,
                "area": l.area,
                "distance_km": m["distance_km"],
                "monthly_total": monthly_cost(l)["total"],
                "risk_level": l.risk_level,
                "match": m["score"],
            }
        )
    best = max(cols, key=lambda c: c["match"])["id"] if cols else None
    return {"columns": cols, "recommended_id": best}


# ---------- Notifications ----------
@router.get("/me/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Notification).filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(20).all()
    return [
        {"id": n.id, "kind": n.kind, "text": n.text, "listing_id": n.listing_id, "link": n.link or (f"/phong/{n.listing_id}" if n.listing_id else None),
         "read": n.read, "created_at": n.created_at.isoformat() + "Z"}
        for n in rows
    ]


@router.get("/me/notifications/unread")
def notifications_unread(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"count": db.query(Notification).filter_by(user_id=user.id, read=False).count()}


class ReadIn(BaseModel):
    id: int | None = None


@router.post("/me/notifications/read")
def notifications_read(body: ReadIn | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Notification).filter_by(user_id=user.id, read=False)
    if body and body.id:
        q = q.filter(Notification.id == body.id)
    q.update({"read": True})
    db.commit()
    return {"ok": True}


@router.get("/me/notification-prefs")
def get_prefs(user: User = Depends(current_user)):
    return prefs_of(user)


@router.put("/me/notification-prefs")
def put_prefs(body: dict[str, bool], user: User = Depends(current_user), db: Session = Depends(get_db)):
    allowed = DEFAULT_PREFS.get(user.role, {})
    user.notification_prefs = {**(user.notification_prefs or {}), **{k: bool(v) for k, v in body.items() if k in allowed}}
    db.commit()
    return prefs_of(user)


# ---------- Reports ----------
class ReportIn(BaseModel):
    reason: Literal["deposit", "wrong_info", "rented", "duplicate", "other"]
    description: str = Field("", max_length=1000)


@router.post("/listings/{listing_id}/report")
def report_listing(listing_id: int, body: ReportIn, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    l = db.get(Listing, listing_id)
    if not l:
        raise HTTPException(404, "Không tìm thấy tin đăng")
    label = "Sinh viên"
    if user and user.school_id:
        s = db.get(School, user.school_id)
        label = f"SV {s.short_name}" if s else label
    db.add(Report(listing_id=l.id, user_id=user.id if user else None, reporter_label=label, reason=body.reason, description=body.description))
    db.flush()
    apply_risk(db, l)
    notify_admins(db, "report", f"Báo cáo mới: {l.title}", "/admin/kiem-duyet", "report")
    notify_savers(db, l.id, "report", f"Tin bạn đã lưu bị báo cáo, hãy cẩn trọng: {l.title}", "report")
    db.commit()
    index_listing(l)
    return {"ok": True, "risk_level": l.risk_level}


# ---------- Account ----------
class ProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(None, max_length=30)
    school_id: int | None = None
    personalize: bool = True


@router.put("/me/profile")
def update_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.full_name, user.phone, user.school_id, user.personalize = body.full_name, body.phone, body.school_id, body.personalize
    db.commit()
    return user_out(user)


@router.get("/me/export")
def export_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        "user": user_out(user),
        "needs": needs_out(db.get(NeedsProfile, user.id), db),
        "saved": [s.listing_id for s in db.query(SavedListing).filter_by(user_id=user.id).all()],
        "reports": [{"listing_id": r.listing_id, "reason": r.reason} for r in db.query(Report).filter_by(user_id=user.id).all()],
    }


@router.delete("/me")
def delete_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "admin":
        raise HTTPException(400, "Không thể xóa tài khoản quản trị")
    db.query(Report).filter_by(user_id=user.id).update({"user_id": None})
    for model in (NeedsProfile, SavedListing, Notification, RecommendationFeedback):
        db.query(model).filter_by(user_id=user.id).delete()
    db.delete(user)
    db.commit()
    return {"deleted": True}
