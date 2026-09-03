import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 프로젝트 루트를 path에 추가하여 core 패키지 import 가능하게
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 계정·답글 이력은 DB 를 쓰므로 requirements-web.txt 에 sqlalchemy 가 들어갔다.
# 더 이상 선택 의존성이 아니다.
from backend.database.migrate import (  # pylint: disable=wrong-import-position
    upgrade_database,
)
from backend.routers import auth, reply  # pylint: disable=wrong-import-position

# 답글 화면만 배포할 때는 분석·크롤링 의존성(pandas, curl_cffi 등)을 설치하지 않는다.
try:
    from backend.routers import (  # pylint: disable=wrong-import-position
        analysis,
        data,
    )
except ImportError:  # pragma: no cover - 배포 구성에 따라 달라짐
    analysis = data = None
    # 슬림 배포에서는 정상이지만, 전체 배포에서 이 로그가 보이면 진짜 고장이다.
    logging.getLogger(__name__).warning(
        "분석·데이터 라우터를 불러오지 못해 비활성화합니다.", exc_info=True
    )

app = FastAPI(title="Review Analysis Dashboard API", version="1.0.0")

# 스키마를 최신 리비전까지 올린다. create_all 과 달리 이미 있는 테이블에
# 생긴 변경(컬럼 추가, 제약 추가)도 따라간다. 최신이면 no-op 이다.
upgrade_database()

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

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
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
    """SPA 라우팅.

    /api 로 시작하는 경로는 폴백하지 않는다. 그러지 않으면 라우터가 빠진
    슬림 배포에서 /api/data/reviews 가 index.html 을 200 으로 돌려주고,
    프론트는 성공으로 처리해 엉뚱한 곳에서 터진다.
    """
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(404, "Not Found")

    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_path):
        return {"detail": "프론트엔드가 빌드되지 않았습니다. frontend에서 npm run build 실행."}

    # startswith 만 쓰면 dist 와 이름이 겹치는 형제 디렉터리(dist-backup 등)로
    # 빠져나갈 수 있다. commonpath 로 경계를 정확히 본다.
    candidate = os.path.normpath(os.path.join(FRONTEND_DIST, full_path))
    if full_path and os.path.isfile(candidate):
        try:
            inside = os.path.commonpath([FRONTEND_DIST, candidate]) == FRONTEND_DIST
        except ValueError:  # 드라이브가 다르면 commonpath 가 던진다
            inside = False
        if inside:
            return FileResponse(candidate)
    return FileResponse(index_path)
