from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from . import models


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.username == username)
    return db.execute(stmt).scalar_one_or_none()


def list_user_roles(db: Session, user: models.User) -> list[str]:
    db.refresh(user)
    return [role.name for role in user.roles]


def ensure_roles(db: Session, role_names: Iterable[str]) -> list[models.Role]:
    roles: list[models.Role] = []
    for name in role_names:
        stmt = select(models.Role).where(models.Role.name == name)
        role = db.execute(stmt).scalar_one_or_none()
        if not role:
            role = models.Role(name=name)
            db.add(role)
            db.flush()
        roles.append(role)
    return roles


def create_refresh_token(
    db: Session,
    user: models.User,
    token_value: str,
    expires_at: datetime,
) -> models.RefreshToken:
    record = models.RefreshToken(
        token=token_value,
        user=user,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_refresh_token(db: Session, token_value: str) -> Optional[models.RefreshToken]:
    stmt = select(models.RefreshToken).where(models.RefreshToken.token == token_value)
    return db.execute(stmt).scalar_one_or_none()


def revoke_refresh_token(db: Session, refresh_token: models.RefreshToken) -> None:
    refresh_token.revoked = True
    db.add(refresh_token)
    db.commit()


def revoke_all_refresh_tokens(db: Session, user: models.User) -> None:
    stmt = (
        update(models.RefreshToken)
        .where(models.RefreshToken.user_id == user.id, models.RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    db.execute(stmt)
    db.commit()


def get_account_setting(db: Session, user: models.User) -> Optional[models.AccountSetting]:
    stmt = select(models.AccountSetting).where(models.AccountSetting.user_id == user.id)
    return db.execute(stmt).scalar_one_or_none()


def create_account_setting(
    db: Session,
    user: models.User,
    status: str,
    trial_ends_at: Optional[datetime],
) -> models.AccountSetting:
    record = models.AccountSetting(
        user=user,
        status=status,
        trial_ends_at=trial_ends_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_account_setting(
    db: Session,
    setting: models.AccountSetting,
    *,
    status: Optional[str] = None,
    trial_ends_at: Optional[datetime] = None,
) -> models.AccountSetting:
    if status is not None:
        setting.status = status
    if trial_ends_at is not None:
        setting.trial_ends_at = trial_ends_at
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting

def revoke_all_refresh_tokens(db: Session, user: models.User) -> None:
       db.query(models.RefreshToken).filter(
           models.RefreshToken.user_id == user.id,
           models.RefreshToken.revoked.is_(False),
       ).update({"revoked": True})
       db.commit()

