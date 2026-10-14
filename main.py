
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine, Base
import models

from auth.routes import router as auth_router
from lomba.routes import router as lomba_router
from proyek.routes import router as proyek_router


app = FastAPI(title="EduMate AI API", version="1.0.0")


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# DATABASE
Base.metadata.create_all(bind=engine)


# ROUTES
app.include_router(auth_router)
app.include_router(lomba_router)
app.include_router(proyek_router)


# ROOT
@app.get("/")
def root():
    return {"message": "EduMate AI Backend is running"}


# TEST DATABASE
@app.get("/test-db")
def test_db():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))

        return {
            "database": "connected",
            "result": result.scalar()
        }
