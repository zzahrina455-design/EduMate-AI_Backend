
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.dependencies import get_current_user
from ai_service import jawab_pertanyaan_chat
from models import User


router = APIRouter(
    prefix="/chat",
    tags=["Chat AI"],
)


class ChatRequest(BaseModel):
    pertanyaan: str = Field(
        min_length=1,
        max_length=10000,
    )


class ChatResponse(BaseModel):
    jawaban: str


@router.post(
    "",
    response_model=ChatResponse,
)
def kirim_pertanyaan(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    pertanyaan = data.pertanyaan.strip()

    if not pertanyaan:
        raise HTTPException(
            status_code=422,
            detail="Pertanyaan tidak boleh kosong.",
        )

    try:
        jawaban = jawab_pertanyaan_chat(pertanyaan)
        return ChatResponse(jawaban=jawaban)

    except Exception:
        raise HTTPException(
            status_code=502,
            detail=(
                "EduMate AI gagal menghasilkan jawaban. "
                "Silakan coba lagi beberapa saat."
            ),
        )
