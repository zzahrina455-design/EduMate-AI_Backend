import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.models.models import User, ChatSession, UserActivity, Competition
from app.auth.dependencies import get_current_user
from app.services.llm_service import call_openrouter
from app.services.document_service import extract_text_from_file

router = APIRouter(prefix="/student/chat", tags=["Student Chat AI"])

UPLOAD_DIR = "uploads/chat_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("")
async def ask_ai_student(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
                file_context = f"\n\n DOKUMEN PROPOSAL / PROJEK MAHASISWA \n{extracted_text[:1500]}\n--- AKHIR DOKUMEN ---"

        # 2. Ambil data lomba dari hasil scraping Instagram
        competitions = (
            db.query(Competition)
            .order_by(Competition.created_at.desc())
            .limit(10)
            .all()
        )

        # JIKA DATABASE KOSONG: Cegah halusinasi LLM
        if not competitions or len(competitions) == 0:
            warning_msg = (
                "⚠️ Database Lomba Instagram Belum Tersedia\n\n"
                "Saat ini belum ada data lomba dari Instagram. "
            )

            new_chat = ChatSession(
                user_id=current_user.id,
                prompt=prompt,
                response=warning_msg,
                uploaded_file_path=saved_file_path,
            )
            db.add(new_chat)
            db.commit()
            db.refresh(new_chat)

            return {
                "id": new_chat.id,
                "prompt": new_chat.prompt,
                "response": new_chat.response,
                "file_path": new_chat.uploaded_file_path,
                "created_at": new_chat.created_at,
            }

        # Format data lomba dari Instagram untuk dikirim ke LLM
        comp_context = "\n DATA LOMBA INSTAGRAM TERVERIFIKASI DI DATABASE \n"
        for idx, c in enumerate(competitions, 1):
            comp_context += (
                f"Lomba #{idx}:\n"
                f"Nama Lomba: {c.title}\n"
                f"Deskripsi / Caption IG: {c.description}\n"
                f"Persyaratan: {c.requirements}\n"
                f"Link Postingan IG: {c.social_media_link or 'Tidak tersedia'}\n\n"
            )
        comp_context += "--- AKHIR DATA LOMBA ---\n"

        # 3. System Prompt
        system_prompt = (
            "Kamu adalah EduMate AI, asisten konsultan kompetisi IT cerdas.\n"
            "TUGAS UTAMA: Analisis projek mahasiswa dan cocokkan dengan lomba dari Instagram di database.\n"
            "ATURAN FORMAT DAN OUTPUT KETAT:\n"
            "1. WAJIB tampilkan maksimal 3 lomba yang paling relevan dan cocok.\n"
            "2. DILARANG menggunakan tanda bintang (*) untuk markdown bold/italic.\n"
            "3. Untuk SETIAP rekomendasi lomba, wajib menyajikan 5 poin :\n"
            "   - Nama Lomba yang relevan dan cocok\n"
            "   - Syarat Lomba\n"
            "   - Peluang Lolos Projek (dalam bentuk persentase %, dan alasannya)\n"
            "   - Apa yang Perlu Diperbaiki oleh projek agar meningkatkan peluang lolos\n"
            "   - Link Lomba (Salin persis link social_media_link dari database)\n"
            "4. DILARANG menggunakan format tabel markdown."
        )

        full_prompt = (
            f"Pertanyaan/Konsultasi Mahasiswa: {prompt}{file_context}\n{comp_context}"
        )

        # 4. Eksekusi LLM Groq
        ai_response = call_openrouter(full_prompt, system_prompt)

        # 5. Simpan Riwayat Percakapan
        new_chat = ChatSession(
            user_id=current_user.id,
            prompt=prompt,
            response=ai_response,
            uploaded_file_path=saved_file_path,
        )
        db.add(new_chat)

        activity = UserActivity(
            user_id=current_user.id,
            activity_type="Tanya AI Lomba (Instagram RAG)",
            description=f"Konsultasi lomba Instagram: {prompt[:40]}...",
        )
        db.add(activity)
        db.commit()
        db.refresh(new_chat)

        return {
            "id": new_chat.id,
            "prompt": new_chat.prompt,
            "response": new_chat.response,
            "file_path": new_chat.uploaded_file_path,
            "created_at": new_chat.created_at,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses pertanyaan: {str(e)}",
        )


@router.get("/history")
async def get_student_chat_history(
    db: Session = Depends(get_db), current_user: User = Depends(
        get_current_user)
):
    chats = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )

    history_data = []
    for chat in chats:
        history_data.append(
            {
                "id": chat.id,
                "prompt": chat.prompt,
                "response": chat.response,
                "file_path": chat.uploaded_file_path,
                "created_at": chat.created_at.isoformat()
                if chat.created_at else None,
            }
        )

    return {"status": "success", "total": len(
        history_data), "data": history_data}


@router.delete("/history/{chat_id}")
async def delete_student_chat_history(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == chat_id, ChatSession.user_id == current_user.id)
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Riwayat percakapan tidak ditemukan.",
        )

    if chat.uploaded_file_path and os.path.exists(chat.uploaded_file_path):
        try:
            os.remove(chat.uploaded_file_path)
        except Exception as e:
            print(f"[FILE DELETE WARNING] Gagal menghapus file: {e}")

    db.delete(chat)
    db.commit()

    return {
        "status": "success",
        "message": f"Riwayat percakapan ID {chat_id} berhasil dihapus.",
    }
