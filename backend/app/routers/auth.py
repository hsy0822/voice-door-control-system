"""注册 / 登录。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser
from app.models import User
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginBody(BaseModel):
    username: str
    password: str
    role: str = Field(pattern="^(resident|admin)$")


def _user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "role": u.role}


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)) -> dict:
    exists = db.scalar(select(User.id).where(User.username == body.username))
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=body.username.strip(),
        password_hash=hash_password(body.password),
        role="resident",
        status="active",
        door_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id), {"role": user.role})
    return {"token": token, "user": _user_out(user)}


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.username == body.username.strip()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已停用")
    if user.role != body.role:
        raise HTTPException(status_code=403, detail="角色与账号不匹配")
    token = create_access_token(str(user.id), {"role": user.role})
    return {"token": token, "user": _user_out(user)}


@router.get("/me")
def me(user: CurrentUser) -> dict:
    return {"user": _user_out(user)}
