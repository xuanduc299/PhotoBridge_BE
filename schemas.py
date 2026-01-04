from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: Optional[str]
    roles: List[str] = Field(default_factory=list)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    roles: List[str]
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20)


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: Optional[str]
    is_active: bool
    roles: List[str]
    created_at: datetime

    @field_validator("roles", mode="before")
    @classmethod
    def normalize_roles(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            normalized: List[str] = []
            for item in value:
                if hasattr(item, "name"):
                    normalized.append(getattr(item, "name"))
                else:
                    normalized.append(str(item))
            return normalized
        return value

    @field_serializer("roles")
    def serialize_roles(self, value: List[Any]) -> List[str]:
        return [role if isinstance(role, str) else str(role) for role in value]


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=72)
    display_name: Optional[str] = None
    roles: List[str] = Field(default_factory=lambda: ["viewer"])
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=72)
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None

