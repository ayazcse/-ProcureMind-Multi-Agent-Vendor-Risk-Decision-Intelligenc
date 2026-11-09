from __future__ import annotations
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.llm_client import llm_status
from app.routers import vendors, documents, requests, review, dashboard, reports

logging.basicConfig(level=logging.INFO)
settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ProcureMind API",
    description="Multi-Agent Vendor Risk & Decision Intelligence System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vendors.router)
app.include_router(documents.router)
app.include_router(requests.router)
app.include_router(review.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {"service": "ProcureMind API", "status": "running", "llm": llm_status()}


@app.get("/api/health")
def health():
    return {"status": "ok", "llm": llm_status()}
