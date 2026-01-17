from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from . import models


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.username == username)
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.get(models.User, user_id)


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


def count_active_refresh_tokens(db: Session, user: models.User, exclude_token: Optional[str] = None) -> int:
    """Count non-revoked, non-expired refresh tokens for a user.
    
    Args:
        db: Database session
        user: User to count tokens for
        exclude_token: Optional token value to exclude from count (used when refreshing)
    """
    from datetime import datetime
    stmt = select(models.RefreshToken).where(
        models.RefreshToken.user_id == user.id,
        models.RefreshToken.revoked.is_(False),
        models.RefreshToken.expires_at > datetime.utcnow()
    )
    if exclude_token:
        stmt = stmt.where(models.RefreshToken.token != exclude_token)
    result = db.execute(stmt).scalars().all()
    return len(result)


def list_users(db: Session) -> list[models.User]:
    stmt = select(models.User).options(selectinload(models.User.roles)).order_by(models.User.id)
    return db.execute(stmt).scalars().unique().all()


def create_user(
    db: Session,
    *,
    username: str,
    password_hash: str,
    display_name: Optional[str],
    is_active: bool,
    role_names: Optional[Iterable[str]] = None,
) -> models.User:
    user = models.User(
        username=username,
        password_hash=password_hash,
        display_name=display_name,
        is_active=is_active,
    )
    if role_names:
        roles = ensure_roles(db, role_names)
        user.roles.extend(roles)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user: models.User,
    *,
    display_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    password_hash: Optional[str] = None,
    role_names: Optional[Iterable[str]] = None,
) -> models.User:
    if display_name is not None:
        user.display_name = display_name
    if is_active is not None:
        user.is_active = is_active
    if password_hash is not None:
        user.password_hash = password_hash
    if role_names is not None:
        roles = ensure_roles(db, role_names)
        user.roles.clear()
        user.roles.extend(roles)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: models.User) -> None:
    db.delete(user)
    db.commit()


def get_account_setting(db: Session, user: models.User) -> Optional[models.AccountSetting]:
    stmt = select(models.AccountSetting).where(models.AccountSetting.user_id == user.id)
    return db.execute(stmt).scalar_one_or_none()


def create_account_setting(
    db: Session,
    user: models.User,
    status: str,
    trial_ends_at: Optional[datetime],
    max_devices: Optional[int] = None,
) -> models.AccountSetting:
    record = models.AccountSetting(
        user=user,
        status=status,
        trial_ends_at=trial_ends_at,
        max_devices=max_devices,
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
    max_devices: Optional[int] = None,
) -> models.AccountSetting:
    if status is not None:
        setting.status = status
    if trial_ends_at is not None:
        setting.trial_ends_at = trial_ends_at
    if max_devices is not None:
        setting.max_devices = max_devices
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting
