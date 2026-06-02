"""依赖注入：当前用户与角色校验。"""

from __future__ import annotations

from typing import Optional

from typing_extensions import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import safe_decode_token

security = HTTPBearer(auto_error=False)


def get_db_session() -> Session:
    yield from get_db()


def get_token_payload(
    cred: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> dict:
    if cred is None or not cred.credentials:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="未登录或缺少令牌",
        )
    payload = safe_decode_token(cred.credentials)
    if not payload:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )
    return payload


def get_current_user(
    payload: Annotated[dict, Depends(get_token_payload)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
    try:
        uid = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
    user = db.get(User, uid)
    if not user or user.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="用户不可用")
    return user


def require_roles(*roles: str):
    def _inner(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="无权执行此操作",
            )
        return user

    return _inner


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
ResidentUser = Annotated[User, Depends(require_roles("resident"))]
AdminUser = Annotated[User, Depends(require_roles("admin"))]
