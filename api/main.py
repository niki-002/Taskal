from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from api.routers import function
from api.database import database_engine
from api.models import Base

BASE_DIR = Path(__file__).resolve().parent.parent # mainの親の親=Taskalディレクトリを基準とする
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Taskal")

app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend") # 静的ファイル配信

app.include_router(function.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=database_engine)

@app.get("/")
def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))