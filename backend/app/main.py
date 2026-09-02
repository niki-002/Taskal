# アプリ起動周りの設定
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers import task
from app.routers import auth


BASE_DIR = Path(__file__).resolve().parent.parent # mainの親の親=Taskalディレクトリを基準とする

app = FastAPI(title="Taskal")

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
