
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas


router = APIRouter(
    prefix="/lomba",
    tags=["Lomba"]
)


# 1. Menampilkan daftar lomba dengan pencarian dan filter
@router.get(
    "/",
    response_model=List[schemas.CompetitionResponse]
)
def get_semua_lomba(
    kategori: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Competition)

    # Filter berdasarkan kategori
    if kategori:
        query = query.filter(
            models.Competition.category.ilike(f"%{kategori}%")
        )

    # Pencarian berdasarkan nama lomba
    if search:
        query = query.filter(
            models.Competition.name.ilike(f"%{search}%")
        )

    # Filter berdasarkan status lomba
    if status:
        query = query.filter(
            models.Competition.status.ilike(status)
        )

    return query.all()


# 2. Menampilkan detail lomba berdasarkan ID
@router.get(
    "/{competition_id}",
    response_model=schemas.CompetitionResponse,
    responses={
        404: {"description": "Data lomba tidak ditemukan"}
    }
)
def get_detail_lomba(
    competition_id: int,
    db: Session = Depends(get_db)
):
    competition = (
        db.query(models.Competition)
        .filter(models.Competition.id == competition_id)
        .first()
    )

    if competition is None:
        raise HTTPException(
            status_code=404,
            detail="Data lomba tidak ditemukan"
        )

    return competition


# 3. Menambahkan data lomba baru
@router.post(
    "/",
    response_model=schemas.CompetitionResponse,
    status_code=201,
    responses={
        500: {
            "description": "Terjadi kesalahan saat menyimpan data lomba"
        }
    }
)
def tambah_lomba(
    competition_data: schemas.CompetitionCreate,
    db: Session = Depends(get_db)
):
    new_competition = models.Competition(
        **competition_data.model_dump()
    )

    try:
        db.add(new_competition)
        db.commit()
        db.refresh(new_competition)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan saat menyimpan data lomba"
        )

    return new_competition


# 4. Menonaktifkan data lomba berdasarkan ID
@router.patch(
    "/{competition_id}/nonaktifkan",
    response_model=schemas.CompetitionResponse,
    responses={
        404: {"description": "Data lomba tidak ditemukan"},
        500: {"description": "Gagal menonaktifkan data lomba"}
    }
)
def nonaktifkan_lomba(
    competition_id: int,
    db: Session = Depends(get_db)
):
    competition = (
        db.query(models.Competition)
        .filter(models.Competition.id == competition_id)
        .first()
    )

    if competition is None:
        raise HTTPException(
            status_code=404,
            detail="Data lomba tidak ditemukan"
        )

    competition.status = "nonaktif"

    try:
        db.commit()
        db.refresh(competition)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Gagal menonaktifkan data lomba"
        )

    return competition
