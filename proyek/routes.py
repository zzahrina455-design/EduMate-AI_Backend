
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from pypdf import PdfReader
from docx import Document

from database import get_db
import models
import schemas
from rag_service import cari_lomba_relevan
from ai_service import analisis_kecocokan_proyek


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/proyek",
    tags=["Dokumen Proyek"],
)

UPLOAD_DIR = "uploads/proyek"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def ekstrak_teks_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    teks = []

    for halaman in reader.pages:
        teks.append(halaman.extract_text() or "")

    return "\n".join(teks).strip()


def ekstrak_teks_docx(file_path: str) -> str:
    dokumen = Document(file_path)

    return "\n".join(
        paragraf.text
        for paragraf in dokumen.paragraphs
        if paragraf.text.strip()
    ).strip()


@router.post("/upload", status_code=201)
async def upload_dokumen_proyek(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    nama_asli = os.path.basename(file.filename or "")

    if not nama_asli:
        raise HTTPException(
            status_code=400,
            detail="Nama file tidak valid.",
        )

    ekstensi = os.path.splitext(nama_asli)[1].lower()

    if ekstensi not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=400,
            detail="Format file harus PDF atau DOCX.",
        )

    isi_file = await file.read()

    if not isi_file:
        raise HTTPException(
            status_code=400,
            detail="File yang diunggah kosong.",
        )

    if len(isi_file) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Ukuran file maksimal 10 MB.",
        )

    nama_tersimpan = f"{uuid4().hex}{ekstensi}"
    lokasi_file = os.path.join(UPLOAD_DIR, nama_tersimpan)

    try:
        with open(lokasi_file, "wb") as tujuan:
            tujuan.write(isi_file)

        if ekstensi == ".pdf":
            teks = ekstrak_teks_pdf(lokasi_file)
        else:
            teks = ekstrak_teks_docx(lokasi_file)

        if not teks:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Teks tidak ditemukan. Pastikan dokumen berisi "
                    "teks yang dapat dibaca, bukan hanya gambar hasil scan."
                ),
            )

        dokumen_baru = models.DokumenProyek(
            nama_file=nama_asli,
            teks_ekstraksi=teks,
        )

        db.add(dokumen_baru)
        db.commit()
        db.refresh(dokumen_baru)

        return {
            "message": "Dokumen berhasil diunggah dan teks berhasil diekstrak.",
            "id": dokumen_baru.id,
            "nama_file": dokumen_baru.nama_file,
            "jumlah_karakter": len(teks),
            "status": "berhasil",
        }

    except HTTPException:
        db.rollback()

        if os.path.exists(lokasi_file):
            os.remove(lokasi_file)

        raise

    except Exception:
        db.rollback()
        logger.exception("Gagal memproses dokumen proyek.")

        if os.path.exists(lokasi_file):
            os.remove(lokasi_file)

        raise HTTPException(
            status_code=500,
            detail="Gagal memproses dokumen. Periksa format dan isi file.",
        )

    finally:
        await file.close()


@router.post(
    "/rekomendasi",
    response_model=schemas.RekomendasiResponse,
)
def rekomendasikan_lomba(
    request: schemas.RekomendasiRequest,
    db: Session = Depends(get_db),
):
    # 1. Cari dokumen proyek.
    dokumen = (
        db.query(models.DokumenProyek)
        .filter(models.DokumenProyek.id == request.dokumen_id)
        .first()
    )

    if dokumen is None:
        raise HTTPException(
            status_code=404,
            detail="Dokumen proyek tidak ditemukan.",
        )

    teks_proyek = dokumen.teks_ekstraksi or ""

    if not teks_proyek.strip():
        raise HTTPException(
            status_code=422,
            detail="Dokumen proyek tidak memiliki teks untuk dianalisis.",
        )

    # 2. Cari kandidat lomba menggunakan RAG.
    try:
        daftar_lomba = cari_lomba_relevan(
            teks_proyek,
            jumlah=5,
        )
    except Exception:
        logger.exception("Pencarian lomba dengan RAG gagal.")
        raise HTTPException(
            status_code=502,
            detail=(
                "Pencarian lomba dengan RAG gagal. "
                "Periksa terminal backend untuk detailnya."
            ),
        )

    if not daftar_lomba:
        return {
            "dokumen_id": dokumen.id,
            "nama_file": dokumen.nama_file,
            "total_rekomendasi": 0,
            "rekomendasi": [],
        }

    # 3. Analisis kandidat menggunakan Mercury.
    try:
        hasil_ai = analisis_kecocokan_proyek(
            teks_proyek,
            daftar_lomba,
        )
    except Exception as error:
        logger.exception("Analisis AI dengan Mercury gagal.")

        # Detail teknis dicatat di terminal, bukan API key.
        raise HTTPException(
            status_code=502,
            detail=(
                f"Analisis AI gagal ({type(error).__name__}). "
                "Periksa pesan error di terminal backend."
            ),
        )

    # 4. Cocokkan hasil AI dengan data lomba asli.
    lomba_berdasarkan_id = {
        item["competition_id"]: item
        for item in daftar_lomba
    }

    rekomendasi = []
    id_yang_sudah_diproses = set()

    for analisis in hasil_ai:
        competition_id = analisis.get("competition_id")
        data_lomba = lomba_berdasarkan_id.get(competition_id)

        if data_lomba is None:
            continue

        if competition_id in id_yang_sudah_diproses:
            continue

        alasan = analisis.get("alasan_kecocokan")
        kelebihan = analisis.get("kelebihan_proyek")
        kekurangan = analisis.get("kekurangan_proyek")
        skor = analisis.get("skor_kecocokan")
        tingkat = analisis.get("tingkat_kecocokan")

        # Abaikan hasil AI yang tidak memenuhi format.
        if not isinstance(alasan, str) or not alasan.strip():
            continue

        if not isinstance(kelebihan, list):
            continue

        if not isinstance(kekurangan, list):
            continue

        if (
            not isinstance(skor, int)
            or isinstance(skor, bool)
            or not 0 <= skor <= 100
        ):
            continue

        if skor >= 80:
            tingkat = "Sangat cocok"
        elif skor >= 60:
            tingkat = "Cocok"
        elif skor >= 40:
            tingkat = "Cukup cocok"
        elif skor >= 20:
            tingkat = "Kurang cocok"
        else:
            tingkat = "Tidak cocok"

        rekomendasi.append({
            "competition_id": competition_id,
            "nama_lomba": data_lomba["nama_lomba"],
            "penyelenggara": data_lomba.get("penyelenggara") or None,
            "kategori": data_lomba["kategori"],
            "skor_kecocokan": skor,
            "tingkat_kecocokan": tingkat,
            "alasan_kecocokan": alasan.strip(),
            "persyaratan": data_lomba.get("persyaratan") or None,
            "kelebihan_proyek": [
                str(item) for item in kelebihan
            ],
            "kekurangan_proyek": [
                str(item) for item in kekurangan
            ],
            "tautan_pendaftaran": (
                data_lomba.get("tautan_pendaftaran") or None
            ),
        })

        id_yang_sudah_diproses.add(competition_id)

    # 5. Urutkan dari skor tertinggi ke terendah.
    rekomendasi.sort(
        key=lambda item: item["skor_kecocokan"],
        reverse=True,
    )

    return {
        "dokumen_id": dokumen.id,
        "nama_file": dokumen.nama_file,
        "total_rekomendasi": len(rekomendasi),
        "rekomendasi": rekomendasi,
    }
