FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 의존성 먼저 복사 → 레이어 캐싱
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 앱 코드 복사
COPY app/ app/
COPY data/ data/

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
