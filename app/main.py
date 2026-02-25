from fastapi import FastAPI
from .routers import tasks
from .db import Base, db_engine
from .models import Task

app = FastAPI()

app.include_router(tasks.router)

@app.on_event("startup")
def on_startup():
    Task.metadata.create_all(bind=db_engine)