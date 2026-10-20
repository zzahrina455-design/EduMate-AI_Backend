from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import bcrypt

from database import get_db
from models import User, ChatSession, PitchingSession, SystemSetting, UserActivity
from schemas import (
    AdminDashboardStats, 
    UserActivityResponse, 
    UserResponse, 
    UserCreateAdmin, 
    UserUpdateProfile
)
from auth.dependencies import get_current_admin_user
from scraper_service import fetch_and_store_ti_competitions

router = APIRouter(prefix="/admin", tags=["Admin"])

# Helper function hash password
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# ==========================================
# 1. DASHBOARD & ACTIVITIES ENDPOINTS
# ==========================================

@router.get("/dashboard", response_model=AdminDashboardStats)
def get_admin_dashboard(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    # Count total registered users
    total_users = db.query(User).count()

    # Count chat & pitching sessions
    try:
        total_chats = db.query(ChatSession).count()
    except Exception:
        total_chats = 0

    try:
        total_pitchings = db.query(PitchingSession).count()
    except Exception:
        total_pitchings = 0

    # Get AI status
    try:
        ai_setting = db.query(SystemSetting).filter(SystemSetting.key == "ai_status").first()
        ai_status = True if (ai_setting and ai_setting.value == "active") else False
    except Exception:
        ai_status = True

    # 7-day usage stats
    today = datetime.utcnow().date()
    seven_days_ago = today - timedelta(days=6)
    
    weekly_stats = []
    for i in range(7):
        current_day = seven_days_ago + timedelta(days=i)
        next_day = current_day + timedelta(days=1)
        
        try:
            chat_count = db.query(ChatSession).filter(
                ChatSession.created_at >= current_day, 
                ChatSession.created_at < next_day
            ).count()
            pitch_count = db.query(PitchingSession).filter(
                PitchingSession.created_at >= current_day, 
                PitchingSession.created_at < next_day
            ).count()
        except Exception:
            chat_count = 0
            pitch_count = 0
        
        weekly_stats.append({
            "date": current_day.strftime("%Y-%m-%d"),
            "day": current_day.strftime("%a"),
            "total_usage": chat_count + pitch_count
        })

    return {
        "total_users": total_users,
        "total_chat_sessions": total_chats,
        "total_pitching_simulations": total_pitchings,
        "ai_status": ai_status,
        "weekly_usage_volume": weekly_stats
    }


@router.get("/activities", response_model=list[UserActivityResponse])
def get_recent_activities(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    try:
        activities = db.query(UserActivity).order_by(UserActivity.created_at.desc()).limit(15).all()
        result = []
        for act in activities:
            result.append({
                "id": act.id,
                "user_name": act.user.name if act.user else "Unknown",
                "user_email": act.user.email if act.user else "Unknown",
                "activity_type": act.activity_type,
                "description": act.description,
                "created_at": act.created_at
            })
        return result
    except Exception:
        return []


@router.post("/toggle-ai-status")
def toggle_ai_status(
    status: bool,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    ai_setting = db.query(SystemSetting).filter(SystemSetting.key == "ai_status").first()
    if not ai_setting:
        ai_setting = SystemSetting(key="ai_status", value="active" if status else "inactive")
        db.add(ai_setting)
    else:
        ai_setting.value = "active" if status else "inactive"
    db.commit()
    return {"message": "Status AI berhasil diperbarui", "status": status}


# ==========================================
# 2. KELOLA USER ENDPOINTS
# ==========================================

@router.get("/users", response_model=list[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    return db.query(User).order_by(User.id.desc()).all()


@router.post("/users", response_model=UserResponse)
def create_user_by_admin(
    user_data: UserCreateAdmin,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar di sistem."
        )

    hashed_pw = hash_password(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password=hashed_pw,
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log Aktivitas
    activity = UserActivity(
        user_id=admin.id,
        activity_type="Kelola User",
        description=f"Admin menambahkan user baru: {new_user.email} ({new_user.role})"
    )
    db.add(activity)
    db.commit()

    return new_user


@router.delete("/users/{user_id}")
def delete_user_by_admin(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan."
        )

    if user_to_delete.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anda tidak dapat menghapus akun Anda sendiri."
        )

    user_email = user_to_delete.email
    db.delete(user_to_delete)
    db.commit()

    # Log Aktivitas
    activity = UserActivity(
        user_id=admin.id,
        activity_type="Kelola User",
        description=f"Admin menghapus user: {user_email}"
    )
    db.add(activity)
    db.commit()

    return {"message": f"User {user_email} berhasil dihapus dari database."}


# ==========================================
# 3. PROFILE ADMIN ENDPOINTS
# ==========================================

@router.get("/profile", response_model=UserResponse)
def get_admin_profile(admin: User = Depends(get_current_admin_user)):
    return admin


@router.put("/profile", response_model=UserResponse)
def update_admin_profile(
    profile_data: UserUpdateProfile,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    if profile_data.name:
        admin.name = profile_data.name

    if profile_data.email and profile_data.email != admin.email:
        existing_email = db.query(User).filter(User.email == profile_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email sudah digunakan oleh akun lain."
            )
        admin.email = profile_data.email

    if profile_data.password:
        admin.password = hash_password(profile_data.password)

    db.commit()
    db.refresh(admin)

    # Log Aktivitas
    activity = UserActivity(
        user_id=admin.id,
        activity_type="Profil Admin",
        description="Admin memperbarui informasi profil akun."
    )
    db.add(activity)
    db.commit()

    return admin


# ==========================================
# 4. RIWAYAT AI ENDPOINTS (ADMIN)
# ==========================================

@router.get("/ai-history")
def get_all_ai_history(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    # Ambil riwayat chat / tanya AI
    chat_logs = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    
    # Ambil riwayat pitching / latihan AI
    pitch_logs = db.query(PitchingSession).order_by(PitchingSession.created_at.desc()).all()
    
    history = []

    for c in chat_logs:
        history.append({
            "id": f"chat-{c.id}",
            "user_name": c.user.name if c.user else "Unknown",
            "user_email": c.user.email if c.user else "Unknown",
            "feature": "Tanya AI",
            "prompt_or_mode": c.prompt,
            "response_summary": c.response[:150] + "..." if len(c.response) > 150 else c.response,
            "file_path": c.uploaded_file_path,
            "created_at": c.created_at
        })

    for p in pitch_logs:
        history.append({
            "id": f"pitch-{p.id}",
            "user_name": p.user.name if p.user else "Unknown",
            "user_email": p.user.email if p.user else "Unknown",
            "feature": "Simulasi Pitching",
            "prompt_or_mode": f"Mode: {p.mode}",
            "response_summary": p.ai_feedback[:150] + "..." if p.ai_feedback and len(p.ai_feedback) > 150 else (p.ai_feedback or "Belum ada umpan balik"),
            "file_path": p.proposal_path,
            "created_at": p.created_at
        })

    # Urutkan berdasarkan tanggal terbaru
    history.sort(key=lambda x: x["created_at"], reverse=True)
    return history


# ==========================================
# 5. SINKRONISASI DATA LOMBA TI (SCRAPER)
# ==========================================

@router.post("/sync-competitions")
async def sync_competitions_data(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    await fetch_and_store_ti_competitions(db)
    
    # Log Aktivitas Admin
    activity = UserActivity(
        user_id=admin.id,
        activity_type="Info Lomba",
        description="Admin memicu sinkronisasi otomatis data lomba TI dari Puspresnas & Devpost."
    )
    db.add(activity)
    db.commit()

    return {"message": "Pembaruan data lomba TI dari Puspresnas & Devpost berhasil dijalankan!"}