from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine, Base
import models
from auth.routes import router as auth_router
from admin_routes import router as admin_router
from student_routes import router as student_router
from student_chat_routes import router as student_chat_router

# =========================
# INISIALISASI DATABASE
# =========================
Base.metadata.create_all(bind=engine)

# =========================
# INISIALISASI APLIKASI
# =========================
app = FastAPI(title="EduMate AI API")

# =========================
# MIDDLEWARE (CORS)
# =========================
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

# =========================
# REGISTRASI ROUTER
# =========================
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(student_router)
app.include_router(student_chat_router)

# =========================
# ROOT & UTILITY ENDPOINTS
# =========================
@app.get("/")
def root():
    return {"message": "EduMate AI Backend is running smoothly!"}

@app.get("/test-db")
def test_db():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {"database": "connected", "result": result.scalar()}