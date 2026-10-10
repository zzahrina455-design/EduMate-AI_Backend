from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from database import get_db
from models import User

# Skema untuk mengambil token dari header Authorization (Bearer token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = "super_secret_key_edumate_ai_2026"
ALGORITHM = "HS256"


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kredensial autentikasi tidak valid atau sudah kedaluwarsa",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


# 2. Fungsi pembatas akses khusus Admin
def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Halaman ini khusus untuk Admin.",
        )
    return current_user


# 3. Fungsi pembatas akses khusus Dosen
def get_current_dosen(current_user: User = Depends(get_current_user)):
    if current_user.role != "dosen" and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Halaman ini khusus untuk Dosen.",
        )
    return current_user


# 4. Fungsi pembatas akses khusus Mahasiswa
def get_current_mahasiswa(current_user: User = Depends(get_current_user)):
    if current_user.role != "mahasiswa" and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Halaman ini khusus untuk Mahasiswa.",
        )
    return current_user
