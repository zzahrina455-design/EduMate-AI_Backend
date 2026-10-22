from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import User, Competition
import schemas # Pastikan import schemas ditambahkan
from auth.dependencies import get_current_user
from scraper_service import fetch_and_store_ti_competitions

router = APIRouter(prefix="/student", tags=["Student"])

# ==========================================
# ENDPOINT PROFIL MAHASISWA
# ==========================================

@router.get("/profile", response_model=schemas.UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Mengambil data profil mahasiswa yang sedang login."""
    return current_user

@router.put("/profile", response_model=schemas.UserProfileResponse)
async def update_profile(
    profile_update: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Memperbarui data profil mahasiswa yang sedang login."""
    
    # Update hanya field yang dikirimkan (tidak None)
    if profile_update.name is not None:
        current_user.name = profile_update.name
    if profile_update.university is not None:
        current_user.university = profile_update.university
    if profile_update.major is not None:
        current_user.major = profile_update.major
    if profile_update.bio is not None:
        current_user.bio = profile_update.bio

    db.commit()
    db.refresh(current_user)
    
    return current_user


# ==========================================
# ENDPOINT KOMPETISI / LOMBA
# ==========================================

@router.get("/competitions")
async def get_competitions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_lomba = db.query(Competition).count()
    
    # Jika database kosong, jalankan scraper otomatis
    if total_lomba == 0:
        print("[AUTO-SCRAPER] Database kosong, mengambil data live dari web...")
        await fetch_and_store_ti_competitions(db)

    competitions = db.query(Competition).order_by(Competition.created_at.desc()).all()
    
    result = []
    for comp in competitions:
        result.append({
            "id": comp.id,
            "title": comp.title,
            "description": comp.description,
            "requirements": comp.requirements,
            "deadline": comp.deadline.strftime("%Y-%m-%d") if comp.deadline else "Segera",
            "social_media_link": comp.social_media_link
        })

    return result