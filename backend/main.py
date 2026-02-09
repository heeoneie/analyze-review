import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ai/ 디렉토리를 path에 추가하여 기존 모듈 import 가능하게
AI_DIR = str(Path(__file__).resolve().parents[1] / "ai")
sys.path.insert(0, AI_DIR)

from backend.routers import analysis, data  # noqa: E402 pylint: disable=wrong-import-position

app = FastAPI(title="Review Analysis Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
