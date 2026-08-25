import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 프로젝트 루트를 path에 추가하여 core 패키지 import 가능하게
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.routers import reply  # pylint: disable=wrong-import-position

# 답글 화면만 배포할 때는 분석·크롤링 의존성(pandas, curl_cffi 등)을 설치하지 않는다.
try:
    from backend.routers import (  # pylint: disable=wrong-import-position
        analysis,
        data,
    )
except ImportError as exc:  # pragma: no cover - 배포 구성에 따라 달라짐
    analysis = data = None
    logging.getLogger(__name__).info("분석·데이터 라우터 비활성화: %s", exc)

app = FastAPI(title="Review Analysis Dashboard API", version="1.0.0")

# 배포 시에는 백엔드가 빌드된 프론트엔드를 같이 서빙하므로 동일 출처가 된다.
# 개발 중 vite dev 서버만 예외로 열어 둔다.
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reply.router, prefix="/api/reply", tags=["reply"])

if data and analysis:
    app.include_router(data.router, prefix="/api/data", tags=["data"])
    app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# 빌드된 프론트엔드가 있으면 같은 서버에서 서빙한다. 사장님은 링크 하나만 열면 된다.
FRONTEND_DIST = os.path.join(PROJECT_ROOT, "frontend", "dist")

if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")),
        name="assets",
    )


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    """SPA 라우팅. API 경로는 위에서 이미 처리됐다."""
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_path):
        return {"detail": "프론트엔드가 빌드되지 않았습니다. frontend에서 npm run build 실행."}

    candidate = os.path.normpath(os.path.join(FRONTEND_DIST, full_path))
    if full_path and candidate.startswith(FRONTEND_DIST) and os.path.isfile(candidate):
        return FileResponse(candidate)
    return FileResponse(index_path)
