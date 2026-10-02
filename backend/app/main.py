from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import checks, health, stats
from app.core.config import CORS_ORIGINS

app = FastAPI(title="API Health Checker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(checks.router)
app.include_router(stats.router)
