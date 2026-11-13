from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import catalog_store, routes_admin, routes_landlord, routes_public, routes_student
from .config import settings
from .db import Base, SessionLocal, engine
from .llm import llm_available
from .search import es

if settings.auto_create_schema:
    Base.metadata.create_all(bind=engine)
Path("uploads").mkdir(exist_ok=True)
with SessionLocal() as _db:
    catalog_store.apply(_db)

app = FastAPI(title=settings.app_name, version="1.0.0", description="API hệ thống tổng hợp, phân tích tin đăng phòng trọ ứng dụng AI")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

for r in (routes_public, routes_student, routes_landlord, routes_admin):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"ok": True, "elasticsearch": bool(es()), "llm": llm_available(), "database": settings.database_url.split(":")[0]}
