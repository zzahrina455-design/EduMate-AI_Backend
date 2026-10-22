from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ==========================================
# 1. AUTH SCHEMAS
# ==========================================

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


# ==========================================
# 2. USER & PROFILE SCHEMAS
# ==========================================

class UserUpdateProfile(BaseModel):
    name: Optional[str] = None
    
class UserCreateAdmin(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "mahasiswa"

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    created_at: datetime
    # Menambahkan field profil agar Admin juga bisa melihat datanya
    university: Optional[str] = None
    major: Optional[str] = None
    bio: Optional[str] = None

    class Config:
        from_attributes = True

# --- Schema Khusus Untuk Fitur Profile ---
class UserProfileBase(BaseModel):
    name: str
    email: str
    university: Optional[str] = None
    major: Optional[str] = None
    bio: Optional[str] = None

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    university: Optional[str] = None
    major: Optional[str] = None
    bio: Optional[str] = None

class UserProfileResponse(UserProfileBase):
    id: int
    role: str

    class Config:
        from_attributes = True


# ==========================================
# 3. ADMIN DASHBOARD SCHEMAS
# ==========================================

class AdminDashboardStats(BaseModel):
    total_users: int
    total_chat_sessions: int
    total_pitching_simulations: int
    ai_status: bool
    weekly_usage_volume: List[dict]

class UserActivityResponse(BaseModel):
    id: int
    user_name: str
    user_email: str
    activity_type: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True