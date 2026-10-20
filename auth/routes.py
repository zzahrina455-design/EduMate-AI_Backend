
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
from models import User
from schemas import UserRegister, UserLogin

router = APIRouter(prefix="/auth", tags=["Authentication"])


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    email = str(user_data.email).strip().lower()

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar.",
        )

    # Pendaftaran umum hanya dapat membuat akun mahasiswa.
    assigned_role = "mahasiswa"
    hashed_pw = hash_password(user_data.password)

    new_user = User(
        name=user_data.name.strip(),
        email=email,
        password=hashed_pw,
        role=assigned_role,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except IntegrityError as e:
        db.rollback()
        print("ERROR REGISTER DATABASE:", repr(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registrasi gagal. Email mungkin sudah terdaftar.",
        ) from e

    except Exception as e:
        db.rollback()
        print("ERROR REGISTER:", repr(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registrasi gagal disimpan.",
        ) from e

    return {
        "message": "Registrasi berhasil",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role,
        },
    }


@router.post("/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    email = str(user_data.email).strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
        )

    token = create_access_token(
        {"sub": user.email, "role": user.role}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }
