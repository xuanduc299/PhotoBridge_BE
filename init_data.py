from __future__ import annotations

import getpass
from typing import Sequence

from sqlalchemy.orm import Session

from . import crud, models
from .database import engine
from .security import hash_password

DEFAULT_ROLES: Sequence[str] = ("admin", "editor", "operator", "viewer")


def init_database() -> None:
    models.Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        crud.ensure_roles(db, DEFAULT_ROLES)
        db.commit()
    print("Đã tạo bảng và role mặc định:", ", ".join(DEFAULT_ROLES))


def create_admin_user() -> None:
    username = input("Username admin mới: ").strip()
    display_name = input("Display name: ").strip() or username
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Nhập lại password: ")
    if password != confirm:
        raise SystemExit("Password không khớp.")

    with Session(bind=engine) as db:
        if crud.get_user_by_username(db, username):
            raise SystemExit("Username đã tồn tại.")
        roles = crud.ensure_roles(db, ["admin"])
        user = models.User(
            username=username,
            password_hash=hash_password(password),
            display_name=display_name,
        )
        user.roles.extend(roles)
        db.add(user)
        db.commit()
    print(f"Đã tạo user admin '{username}'.")


if __name__ == "__main__":
    init_database()
    if input("Tạo tài khoản admin ngay? (y/N): ").strip().lower() == "y":
        create_admin_user()

