"""Tạo thông báo trong hệ thống, tôn trọng cài đặt nhận thông báo của từng người."""

from sqlalchemy.orm import Session

from .models import Notification, SavedListing, User

DEFAULT_PREFS = {
    "student": {"price_drop": True, "match": True, "report": True, "weekly": False},
    "landlord": {"contact": True, "approved": True, "price_tip": True, "monthly": False},
    "admin": {"report": True, "pending": True, "source_error": True},
}


def prefs_of(user: User) -> dict:
    return {**DEFAULT_PREFS.get(user.role, {}), **(user.notification_prefs or {})}


def notify(db: Session, user: User | None, kind: str, text: str, link: str | None = None, pref: str | None = None, listing_id: int | None = None) -> None:
    if not user or (pref and not prefs_of(user).get(pref, True)):
        return
    db.add(Notification(user_id=user.id, kind=kind, text=text[:255], link=link, listing_id=listing_id))


def notify_admins(db: Session, kind: str, text: str, link: str, pref: str) -> None:
    for a in db.query(User).filter_by(role="admin").all():
        notify(db, a, kind, text, link, pref)


def notify_savers(db: Session, listing_id: int, kind: str, text: str, pref: str) -> None:
    for s in db.query(SavedListing).filter_by(listing_id=listing_id).all():
        notify(db, db.get(User, s.user_id), kind, text, f"/phong/{listing_id}", pref, listing_id)
