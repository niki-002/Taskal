FROM python:3.12-slim AS base

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# 開発用：テスト用の依存パッケージ（pytest・httpx）を追加する
FROM base AS dev

RUN pip install --no-cache-dir -r requirements-dev.txt
