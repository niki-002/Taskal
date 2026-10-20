# アプリ起動周りの設定
from pathlib import Path
from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.errors import register_exception_handlers
from app.routers import schedule, task, user


BASE_DIR = Path(__file__).resolve().parent.parent # mainの親の親=Taskalディレクトリを基準とする

app = FastAPI(title="Taskal")

register_exception_handlers(app)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(user.router)
api_v1.include_router(task.router)
api_v1.include_router(schedule.router)

app.include_router(api_v1)

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
