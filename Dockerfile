# 1단계: 프론트엔드 빌드
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2단계: FastAPI 가 빌드된 프론트엔드를 함께 서빙
FROM python:3.12-slim
WORKDIR /app

COPY requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt

COPY backend/ ./backend/
COPY core/ ./core/
# 기동 시 alembic upgrade head 를 돌리므로 마이그레이션 스크립트가 있어야 한다.
COPY alembic.ini ./alembic.ini
COPY migrations/ ./migrations/
COPY data/store_menu.json ./data/store_menu.json
COPY --from=frontend /app/frontend/dist ./frontend/dist

# DB 는 /app/data 가 아니라 여기에 둔다. /app/data 에 볼륨을 걸면 이미지에
# 들어 있는 store_menu.json 이 볼륨 초기 복사본으로 굳어서, 메뉴를 고쳐도
# 옛 파일이 계속 쓰인다. 쓰기 대상만 따로 떼어 놓는다.
RUN mkdir -p /app/var

# 루트로 돌릴 이유가 없다. 컨테이너가 뚫렸을 때 피해 범위를 줄인다.
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
