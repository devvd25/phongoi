from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


class School(Base):
    __tablename__ = "schools"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    short_name: Mapped[str] = mapped_column(String(60))
    district: Mapped[str] = mapped_column(String(60))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    aliases: Mapped[list] = mapped_column(JSON, default=list)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="student")  # student | landlord | admin
    phone: Mapped[str | None] = mapped_column(String(30))
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"))
    bio: Mapped[str | None] = mapped_column(Text)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    address_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    id_verification: Mapped[str] = mapped_column(String(20), default="none")  # none | pending | verified
    personalize: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_prefs: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class CatalogItem(Base):
    """Mục danh mục do admin thêm: tiện ích mới, từ đồng nghĩa bổ sung, từ khóa lừa đảo."""

    __tablename__ = "catalog_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))  # amenity | synonyms | scam_keyword
    key: Mapped[str] = mapped_column(String(60), index=True)
    label: Mapped[str] = mapped_column(String(120), default="")
    data: Mapped[list] = mapped_column(JSON, default=list)


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[int] = mapped_column(Integer, index=True)  # VND / tháng
    area: Mapped[float | None] = mapped_column(Float)
    district: Mapped[str] = mapped_column(String(60), index=True)
    street: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(255), default="")
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    room_type: Mapped[str] = mapped_column(String(20), default="phong_tro")
    max_people: Mapped[int | None] = mapped_column(Integer)
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    deposit_months: Mapped[int | None] = mapped_column(Integer)
    electricity_price: Mapped[int | None] = mapped_column(Integer)
    water_price: Mapped[int | None] = mapped_column(Integer)  # VND / người / tháng
    wifi_price: Mapped[int | None] = mapped_column(Integer)
    images: Mapped[list] = mapped_column(JSON, default=list)
    image_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|pending|hidden|rented
    available_from: Mapped[date | None] = mapped_column(Date)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    poster_account_age_days: Mapped[int | None] = mapped_column(Integer)
    source_count: Mapped[int] = mapped_column(Integer, default=1)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(10), default="low")  # low|medium|high
    risk_reasons: Mapped[list] = mapped_column(JSON, default=list)
    risk_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    quality_score: Mapped[float] = mapped_column(Float, default=7.0)
    ai_summary: Mapped[list] = mapped_column(JSON, default=list)
    views: Mapped[int] = mapped_column(Integer, default=0)
    contacts: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    posted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    sources: Mapped[list["ListingSource"]] = relationship(back_populates="listing", cascade="all, delete-orphan")


class ListingSource(Base):
    __tablename__ = "listing_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    source_name: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(500))
    posted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    listing: Mapped[Listing] = relationship(back_populates="sources")


class ListingStat(Base):
    """Thống kê theo ngày cho từng tin (dùng cho trang chủ trọ)."""

    __tablename__ = "listing_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    contacts: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)


class NeedsProfile(Base):
    __tablename__ = "needs_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    budget_min: Mapped[int | None] = mapped_column(Integer)
    budget_max: Mapped[int | None] = mapped_column(Integer)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"))
    max_distance_km: Mapped[float | None] = mapped_column(Float)
    districts: Mapped[list] = mapped_column(JSON, default=list)
    room_types: Mapped[list] = mapped_column(JSON, default=list)
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    max_people: Mapped[int | None] = mapped_column(Integer)
    transport: Mapped[str] = mapped_column(String(20), default="xe_may")
    move_in: Mapped[str | None] = mapped_column(String(40))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SavedListing(Base):
    __tablename__ = "saved_listings"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    price_at_save: Mapped[int] = mapped_column(Integer)
    contacted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # match | price_drop | report | daily | contact | pending | approved | hidden | source_error
    text: Mapped[str] = mapped_column(String(255))
    listing_id: Mapped[int | None] = mapped_column(Integer)
    link: Mapped[str | None] = mapped_column(String(255))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reporter_label: Mapped[str] = mapped_column(String(80), default="Sinh viên")
    reason: Mapped[str] = mapped_column(String(40))  # deposit | wrong_info | rented | duplicate | other
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="new")  # new | processing | resolved | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    listing_id: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SearchLog(Base):
    __tablename__ = "search_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String(500))
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    engine: Mapped[str] = mapped_column(String(10), default="rule")
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class CrawlSource(Base):
    __tablename__ = "crawl_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))  # sample | scrapy | playwright | internal | manual
    spider: Mapped[str | None] = mapped_column(String(60))
    profile_id: Mapped[str | None] = mapped_column(String(80), unique=True, index=True)
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    connector_type: Mapped[str] = mapped_column(String(30), default="html_static")
    integration_status: Mapped[str] = mapped_column(String(30), default="legal_review")
    start_url: Mapped[str] = mapped_column(String(500), default="")
    # Selector cho spider "generic" và xác nhận đã kiểm tra điều khoản/robots.txt của nguồn.
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    frequency_minutes: Mapped[int] = mapped_column(Integer, default=15)
    rate_limit: Mapped[str] = mapped_column(String(40), default="1 yêu cầu / 2 giây")
    max_pages: Mapped[int] = mapped_column(Integer, default=5)
    obey_robots: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok | running | error | paused
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    health_score: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime)
    terms_url: Mapped[str | None] = mapped_column(String(500))
    robots_url: Mapped[str | None] = mapped_column(String(500))
    approval_notes: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_by_id: Mapped[int | None] = mapped_column(Integer)


class CrawlRun(Base):
    __tablename__ = "crawl_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("crawl_sources.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | success | partial | error
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    dup_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    duration_s: Mapped[int | None] = mapped_column(Integer)
    collected: Mapped[int] = mapped_column(Integer, default=0)
    cleaned: Mapped[int] = mapped_column(Integer, default=0)
    extracted: Mapped[int] = mapped_column(Integer, default=0)
    deduped: Mapped[int] = mapped_column(Integer, default=0)
    scored: Mapped[int] = mapped_column(Integer, default=0)
    indexed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="success")


class ExtractionIssue(Base):
    __tablename__ = "extraction_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    snippet: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AIUsage(Base):
    """Tổng hợp lượt gọi LLM theo ngày, tác vụ và mô hình."""

    __tablename__ = "ai_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    task: Mapped[str] = mapped_column(String(20))  # extract | query | summary
    model: Mapped[str] = mapped_column(String(60))
    calls: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_vnd: Mapped[float] = mapped_column(Float, default=0)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
