from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import get_db
from app.models.models import User, Competition
from app.schemas import schemas
from app.auth.dependencies import get_current_user
from app.services.apify_service import fetch_and_store_instagram_competitions

router = APIRouter(prefix="/student", tags=["Student"])

# ==========================================
# ENDPOINT PROFIL MAHASISWA
# ==========================================


@router.get("/profile", response_model=schemas.UserProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Mengambil data profil mahasiswa yang sedang login."""
    return current_user


@router.put("/profile", response_model=schemas.UserProfileResponse)
async def update_profile(
    profile_update: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Memperbarui data profil mahasiswa yang sedang login."""

    # Update hanya field yang dikirimkan (tidak None) sesuai skema baru
    if profile_update.name is not None:
        current_user.name = profile_update.name
    if profile_update.nim is not None:
        current_user.nim = profile_update.nim
    if profile_update.faculty is not None:
        current_user.faculty = profile_update.faculty
    if profile_update.major is not None:
        current_user.major = profile_update.major
    if profile_update.phone is not None:
        current_user.phone = profile_update.phone

    db.commit()
    db.refresh(current_user)

    return current_user


# ==========================================
# ENDPOINT KOMPETISI / LOMBA
# ==========================================


@router.get("/competitions")
async def get_competitions(db: Session = Depends(get_db)):
    # Cek apakah data kompetisi kosong
    competitions = db.query(Competition).all()

    if not competitions:
        # Jika kosong, otomatis tarik dari Instagram via Apify
        try:
            await fetch_and_store_instagram_competitions(db)
            competitions = db.query(Competition).all()
        except Exception as e:
            print(f"[AUTO-APIFY ERROR] Gagal menarik data otomatis: {e}")

    return competitions
