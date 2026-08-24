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
COPY data/store_menu.json ./data/store_menu.json
COPY --from=frontend /app/frontend/dist ./frontend/dist

# 루트로 돌릴 이유가 없다. 컨테이너가 뚫렸을 때 피해 범위를 줄인다.
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
