
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =========================
# Schema Autentikasi
# =========================

class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


# =========================
# Schema Data Lomba
# =========================

class CompetitionCreate(BaseModel):
    name: str
    organizer: Optional[str] = None
    category: str = "Umum"
    description: Optional[str] = None
    requirements: Optional[str] = None
    deadline: Optional[datetime] = None
    source_url: Optional[str] = None
    registration_url: Optional[str] = None
    status: str = "aktif"


class CompetitionResponse(CompetitionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None


# =========================
# Schema Hasil Rekomendasi
# =========================

class HasilRekomendasi(BaseModel):
    competition_id: int
    nama_lomba: str
    penyelenggara: Optional[str] = None
    kategori: str
    skor_kecocokan: int
    tingkat_kecocokan: str
    alasan_kecocokan: str
    persyaratan: Optional[str] = None
    kelebihan_proyek: list[str]
    kekurangan_proyek: list[str]
    tautan_pendaftaran: Optional[str] = None


class RekomendasiRequest(BaseModel):
    dokumen_id: int


class RekomendasiResponse(BaseModel):
    dokumen_id: int
    nama_file: str
    total_rekomendasi: int
    rekomendasi: list[HasilRekomendasi]
