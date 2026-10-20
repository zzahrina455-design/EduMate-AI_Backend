from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import SECRET_KEY, ALGORITHM
from database import get_db
from models import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kredensial autentikasi tidak valid atau sudah kedaluwarsa.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        email = payload.get("sub")

        if not email:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        raise credentials_exception

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Halaman ini khusus untuk Admin.",
        )

    return current_user


def get_current_dosen(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("dosen", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Halaman ini khusus untuk Dosen.",
        )

    return current_user


def get_current_mahasiswa(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("mahasiswa", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Halaman ini khusus untuk Mahasiswa.",
        )

    return current_user