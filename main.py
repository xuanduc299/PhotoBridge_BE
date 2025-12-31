from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .config import get_settings
from .database import engine
from .deps import get_db
from .security import create_access_token, generate_refresh_token, verify_password


TRIAL_POLICY = {"operator": 1}  # days

models.Base.metadata.create_all(bind=engine)
settings = get_settings()

app = FastAPI(title="PhotoBridge Auth API", version="1.2.0")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=schemas.LoginResponse, tags=["auth"])
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)) -> schemas.LoginResponse:
    user = crud.get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai username hoặc password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị vô hiệu hóa.")
    roles = [role.name for role in user.roles]
    _ensure_account_entitlement(db, user, roles)
    return _build_session_response(user, roles, db)


@app.post("/auth/refresh", response_model=schemas.LoginResponse, tags=["auth"])
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)) -> schemas.LoginResponse:
    if not payload.refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ.")
    record = crud.get_refresh_token(db, payload.refresh_token)
    if not record or record.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ hoặc đã bị thu hồi.")
    if record.expires_at < datetime.utcnow():
        crud.revoke_refresh_token(db, record)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token đã hết hạn.")
    user = record.user
    if not user.is_active:
        crud.revoke_refresh_token(db, record)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị vô hiệu hóa.")
    crud.revoke_refresh_token(db, record)
    roles = [role.name for role in user.roles]
    _ensure_account_entitlement(db, user, roles)
    return _build_session_response(user, roles, db)


def _build_session_response(user: models.User, roles: list[str], db: Session) -> schemas.LoginResponse:
    crud.revoke_all_refresh_tokens(db, user)
    access_token = create_access_token(subject=user.username, roles=roles)
    refresh_value = generate_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    refresh_record = crud.create_refresh_token(db, user, refresh_value, expires_at)
    user_out = schemas.UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=roles,
    )
    return schemas.LoginResponse(
        access_token=access_token,
        refresh_token=refresh_record.token,
        roles=roles,
        user=user_out,
    )


def _ensure_account_entitlement(db: Session, user: models.User, roles: list[str]) -> None:
    setting = crud.get_account_setting(db, user)
    if setting is None:
        if trial_days := _trial_duration_for_roles(roles):
            trial_end = datetime.utcnow() + timedelta(days=trial_days)
            setting = crud.create_account_setting(db, user, status="trial", trial_ends_at=trial_end)
        else:
            setting = crud.create_account_setting(db, user, status="active", trial_ends_at=None)

    if setting.status == "locked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa.")
    if setting.status == "expired":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã hết hạn.")
    if setting.status == "trial":
        if setting.trial_ends_at and setting.trial_ends_at < datetime.utcnow():
            crud.update_account_setting(db, setting, status="expired")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã hết thời gian dùng thử.",
            )


def _trial_duration_for_roles(roles: list[str]) -> Optional[int]:
    durations = [TRIAL_POLICY[role] for role in roles if role in TRIAL_POLICY]
    if not durations:
        return None
    return min(durations)

