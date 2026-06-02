"""住户访客临时授权。"""

from __future__ import annotations

import datetime as dt
import secrets
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import ResidentUser
from app.models import AccessLog, VisitorAuth

router = APIRouter(prefix="/visitor", tags=["visitor"])


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _cleanup_expired(db: Session) -> None:
    now = _utcnow()
    db.execute(delete(VisitorAuth).where(VisitorAuth.expires_at.is_not(None)).where(VisitorAuth.expires_at < now))


def _gen_token(db: Session) -> str:
    for _ in range(20):
        t = secrets.token_hex(4).upper()
        exists = db.scalar(select(VisitorAuth.id).where(VisitorAuth.token == t))
        if not exists:
            return t
    raise HTTPException(status_code=500, detail="无法生成唯一口令")


class VisitorCreateBody(BaseModel):
    userId: Union[str, int]
    type: str = Field(pattern="^(once|hour|two_hour)$")


@router.post("/auth")
def create_visitor_auth(
    user: ResidentUser,
    body: VisitorCreateBody,
    db: Session = Depends(get_db),
) -> dict:
    try:
        uid = int(body.userId)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="用户 ID 无效")
    if uid != user.id:
        raise HTTPException(status_code=403, detail="只能为自己创建访客授权")

    _cleanup_expired(db)
    token = _gen_token(db)
    now = _utcnow()
    expires: Optional[dt.datetime] = None
    if body.type == "hour":
        expires = now + dt.timedelta(hours=1)
    elif body.type == "two_hour":
        expires = now + dt.timedelta(hours=2)

    row = VisitorAuth(
        creator_user_id=user.id,
        token=token,
        auth_type=body.type,
        expires_at=expires,
        used=False,
    )
    db.add(row)
    db.add(
        AccessLog(
            user_id=user.id,
            username=user.username,
            mode="self",
            success=True,
            result="创建访客临时授权",
            abnormal=False,
            detail=f"visitor_auth id={token}",
        )
    )
    db.commit()
    db.refresh(row)
    return {"token": token, "code": token, "id": row.id, "expireAt": expires.isoformat() if expires else None}


@router.get("/list")
def list_visitor_auth(
    user: ResidentUser,
    db: Session = Depends(get_db),
    userId: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
) -> dict:
    _cleanup_expired(db)
    db.commit()
    if userId is not None:
        try:
            if int(userId) != user.id:
                raise HTTPException(status_code=403, detail="无权查看他人授权")
        except ValueError:
            raise HTTPException(status_code=400, detail="用户 ID 无效")

    page = max(1, page)
    page_size = min(100, max(1, pageSize))
    q = select(VisitorAuth).where(VisitorAuth.creator_user_id == user.id).order_by(VisitorAuth.created_at.desc())
    rows = db.scalars(q.offset((page - 1) * page_size).limit(page_size + 1)).all()
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    now = _utcnow()
    out = []
    for r in rows:
        expired = (r.expires_at is not None and r.expires_at < now) or (
            r.auth_type == "once" and r.used
        )
        out.append(
            {
                "id": r.id,
                "token": r.token,
                "code": r.token,
                "authType": r.auth_type,
                "createdAt": r.created_at.isoformat(),
                "expireAt": r.expires_at.isoformat() if r.expires_at else None,
                "expiresAt": r.expires_at.isoformat() if r.expires_at else None,
                "used": r.used,
                "expired": expired,
            }
        )
    return {"list": out, "hasMore": has_more}


@router.delete("/{auth_id}")
def delete_visitor_auth(
    auth_id: int,
    user: ResidentUser,
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(VisitorAuth, auth_id)
    if not row or row.creator_user_id != user.id:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(row)
    db.commit()
    return {"success": True}
