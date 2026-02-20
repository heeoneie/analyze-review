import os
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 프로젝트 루트를 path에 추가하여 core 패키지 import 가능하게
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.routers import (  # pylint: disable=wrong-import-position
    analysis,
    data,
    reply,
    risk,
)

app = FastAPI(title="Review Analysis Dashboard API", version="1.0.0")


def _get_allowed_origins() -> List[str]:
    raw_origins = os.getenv("ALLOWED_ORIGINS", "")
    if not raw_origins:
        return ["http://localhost:5173", "http://localhost:3000"]
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(reply.router, prefix="/api/reply", tags=["reply"])
app.include_router(risk.router, prefix="/api/risk", tags=["risk"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
