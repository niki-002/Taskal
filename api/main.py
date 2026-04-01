from fastapi import FastAPI
from routers import function
from database import database_engine, Base

app = FastAPI(title="Taskal")

app.include_router(function.router)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=database_engine)