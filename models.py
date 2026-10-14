
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="mahasiswa")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Competition(Base):
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    organizer = Column(String(255), nullable=True)
    category = Column(String(100), nullable=False, default="Umum")
    description = Column(String(2000), nullable=True)
    requirements = Column(String(2000), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    source_url = Column(String(500), nullable=True)
    registration_url = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False, default="aktif")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DokumenProyek(Base):
    __tablename__ = "dokumen_proyek"

    id = Column(Integer, primary_key=True, index=True)
    nama_file = Column(String(255), nullable=False)
    teks_ekstraksi = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
