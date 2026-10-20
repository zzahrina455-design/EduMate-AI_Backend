import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import User, ChatSession, UserActivity, Competition
from auth.dependencies import get_current_user
from llm_service import call_openrouter
from document_service import extract_text_from_file

router = APIRouter(prefix="/student/chat", tags=["Student Chat AI"])

UPLOAD_DIR = "uploads/chat_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("")
async def ask_ai_student(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    saved_file_path = None
    file_context = ""

    try:
        # 1. Ekstrak teks dari berkas jika diunggah
        if file and file.filename:
            file_ext = os.path.splitext(file.filename)[1].lower()
            filename = f"{current_user.id}_{int(datetime.now().timestamp())}{file_ext}"
            saved_file_path = os.path.join(UPLOAD_DIR, filename)

            with open(saved_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            extracted_text = extract_text_from_file(saved_file_path, file_ext)
            if extracted_text:
                file_context = f"\n\n--- DOKUMEN PROPOSAL MAHASISWA ---\n{extracted_text[:4000]}\n--- AKHIR DOKUMEN ---"

        # 2. Ambil data lomba ASLI dari database PostgreSQL
        competitions = db.query(Competition).all()
        
        # JIKA DATABASE KOSONG: Cegah pemanggilan LLM agar tidak terjadi halusinasi
        if not competitions or len(competitions) == 0:
            warning_msg = (
                "⚠️ Database Lomba Belum Tersedia\n\n"
                "Saat ini belum ada data lomba terverifikasi di database EduMate AI. "
                "Silakan minta Admin untuk menjalankan Scraper Lomba terlebih dahulu agar rekomendasi lomba dapat ditampilkan secara akurat dan real-time."
            )
            
            new_chat = ChatSession(
                user_id=current_user.id,
                prompt=prompt,
                response=warning_msg,
                uploaded_file_path=saved_file_path
            )
            db.add(new_chat)
            db.commit()
            db.refresh(new_chat)

            return {
                "id": new_chat.id,
                "prompt": new_chat.prompt,
                "response": new_chat.response,
                "file_path": new_chat.uploaded_file_path,
                "created_at": new_chat.created_at
            }

        # Format data lomba asli untuk dikirim ke LLM
        comp_context = "\n--- DATA LOMBA TERVERIFIKASI DI DATABASE EDUMATE AI ---\n"
        for idx, c in enumerate(competitions, 1):
            deadline_str = c.deadline.strftime('%d %B %Y') if c.deadline else 'Cek Situs Resmi'
            comp_context += (
                f"Lomba #{idx}:\n"
                f"Nama Lomba: {c.title}\n"
                f"Deskripsi: {c.description}\n"
                f"Persyaratan: {c.requirements}\n"
                f"Deadline Asli: {deadline_str}\n"
                f"Link Resmi: {c.social_media_link or 'Tidak tersedia'}\n\n"
            )
        comp_context += "--- AKHIR DATA LOMBA ---\n"

        # 3. System Prompt Ketat: Maksimal 3 Lomba, Tanpa Tanda Bintang & RAG Nyata
        system_prompt = (
            "Kamu adalah EduMate AI, asisten rekomendasi lomba akademis TIK.\n"
            "ATURAN FORMAT DAN DATA SANGAT KETAT:\n"
            "1. WAJIB TAMPILKAN HANYA MAXIMAL 3 LOMBA YANG PALING COCOK DAN PALING RELEVAN dengan proposal/projek mahasiswa.\n"
            "2. DILARANG GUNAKAN TANDA BINTANG (*) UNTUK BOLD ATAU LIST. BERSIHKAN SEMUA TANDA BINTANG KELUARAN.\n"
            "3. Gunakan angka biasa (1, 2, 3) atau strip (-) untuk daftar poin.\n"
            "4. HANYA rekomendasikan lomba yang ada dalam section 'DATA LOMBA TERVERIFIKASI DI DATABASE'.\n"
            "5. Salin Deadline Asli dan Link Resmi KETAT PERSIS seperti yang tercantum di database. DILARANG MENGARANG ATAU MENYAMARATAKAN TANGGAL DEADLINE.\n"
            "6. DILARANG menggunakan format TABEL Markdown.\n\n"
            "GUNAKAN FORMAT OUTPUT BERSIH DENGAN STRUKTUR INI:\n\n"
            "ANALISIS RINGKAS PROJEK\n"
            "- Nama/Topik Projek: [Isi topik]\n"
            "- Potensi Kunci Projek: [Isi potensi]\n\n"
            "REKOMENDASI 3 LOMBA TERBAIK\n\n"
            "1. [Nama Lomba Pertama Persis Database]\n"
            "- Deadline Asli: [Tanggal Deadline Persis Database]\n"
            "- Persyaratan: [Persyaratan Persis Database]\n"
            "- Kelebihan Projek Ini: [Alasan kontekstual kecocokan]\n"
            "- Sisi yang Perlu Ditingkatkan: [Saran perbaikan]\n"
            "- Link Resmi Lomba: [Link Persis Database]\n\n"
            "2. [Nama Lomba Kedua Persis Database]\n"
            "- Deadline Asli: [Tanggal Deadline Persis Database]\n"
            "- Persyaratan: [Persyaratan Persis Database]\n"
            "- Kelebihan Projek Ini: [Alasan kontekstual kecocokan]\n"
            "- Sisi yang Perlu Ditingkatkan: [Saran perbaikan]\n"
            "- Link Resmi Lomba: [Link Persis Database]\n\n"
            "3. [Nama Lomba Ketiga Persis Database]\n"
            "- Deadline Asli: [Tanggal Deadline Persis Database]\n"
            "- Persyaratan: [Persyaratan Persis Database]\n"
            "- Kelebihan Projek Ini: [Alasan kontekstual kecocokan]\n"
            "- Sisi yang Perlu Ditingkatkan: [Saran perbaikan]\n"
            "- Link Resmi Lomba: [Link Persis Database]"
        )

        full_prompt = f"Pertanyaan Mahasiswa: {prompt}{file_context}\n{comp_context}"

        # 4. Eksekusi LLM
        ai_response = call_openrouter(full_prompt, system_prompt)

        # 5. Simpan Riwayat
        new_chat = ChatSession(
            user_id=current_user.id,
            prompt=prompt,
            response=ai_response,
            uploaded_file_path=saved_file_path
        )
        db.add(new_chat)

        activity = UserActivity(
            user_id=current_user.id,
            activity_type="Tanya AI Lomba (Top 3 Clean RAG)",
            description=f"Konsultasi proposal: {prompt[:40]}..."
        )
        db.add(activity)
        db.commit()
        db.refresh(new_chat)

        return {
            "id": new_chat.id,
            "prompt": new_chat.prompt,
            "response": new_chat.response,
            "file_path": new_chat.uploaded_file_path,
            "created_at": new_chat.created_at
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses pertanyaan: {str(e)}"
        )

@router.get("/history")
async def get_student_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengambil seluruh riwayat konsultasi Tanya AI milik mahasiswa yang sedang login.
    """
    chats = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )

    history_data = []
    for chat in chats:
        history_data.append({
            "id": chat.id,
            "prompt": chat.prompt,
            "response": chat.response,
            "file_path": chat.uploaded_file_path,
            "created_at": chat.created_at.isoformat() if chat.created_at else None
        })

    return {
        "status": "success",
        "total": len(history_data),
        "data": history_data
    }


@router.delete("/history/{chat_id}")
async def delete_student_chat_history(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menghapus riwayat percakapan spesifik milik mahasiswa.
    """
    chat = (
        db.query(ChatSession)
        .filter(ChatSession.id == chat_id, ChatSession.user_id == current_user.id)
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Riwayat percakapan tidak ditemukan."
        )

    # Hapus file fisik jika ada
    if chat.uploaded_file_path and os.path.exists(chat.uploaded_file_path):
        try:
            os.remove(chat.uploaded_file_path)
        except Exception as e:
            print(f"[FILE DELETE WARNING] Gagal menghapus file: {e}")

    db.delete(chat)
    db.commit()

    return {
        "status": "success",
        "message": f"Riwayat percakapan ID {chat_id} berhasil dihapus."
    }