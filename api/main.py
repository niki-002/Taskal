# アプリ起動周りの設定
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .routers import task, auth
from .db import db_engine
from .models.Base import Base


BASE_DIR = Path(__file__).resolve().parent.parent # mainの親の親=Taskalディレクトリを基準とする
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Taskal")

# 静的ファイル配信
app.mount(
    "/frontend",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="frontend"
)

app.include_router(task.router)
app.include_router(auth.router)

origins = [
    "http://127.0.0.1:8000/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=db_engine)


@app.get("/")
def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))