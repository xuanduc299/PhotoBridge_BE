from __future__ import annotations

from dataclasses import dataclass
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from . import crud, models
from .database import SessionLocal
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@dataclass
class AuthenticatedUser:
    user: models.User
    roles: list[str]


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> AuthenticatedUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exception
    username = payload.get("sub")
    if not username:
        raise credentials_exception
    user = crud.get_user_by_username(db, username)
    if not user or not user.is_active:
        raise credentials_exception
    roles = crud.list_user_roles(db, user)
    return AuthenticatedUser(user=user, roles=roles)


def require_admin(auth: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if "admin" not in auth.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới được phép truy cập.",
        )
    return auth

