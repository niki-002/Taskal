from fastapi import FastAPI
from .routers import function
from .database import Base, db_engine
from .models import Task

app = FastAPI()

app.include_router(function.router)

@app.on_event("startup")
def on_startup():
    Task.metadata.create_all(bind=db_engine)