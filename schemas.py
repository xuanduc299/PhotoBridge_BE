from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


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

