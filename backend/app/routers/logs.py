"""住户出入日志。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import ResidentUser
from app.models import AccessLog

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/user")
def user_logs(
    user: ResidentUser,
    db: Session = Depends(get_db),
    userId: Optional[str] = None,
    page: int = 1,
    pageSize: int = 20,
) -> dict:
    if userId is None:
        raise HTTPException(status_code=400, detail="缺少 userId")
    try:
        uid = int(userId)
    except ValueError:
        raise HTTPException(status_code=400, detail="用户 ID 无效")
    if uid != user.id:
        raise HTTPException(status_code=403, detail="只能查看本人日志")

    page = max(1, page)
    ps = min(100, max(1, pageSize))
    total = db.scalar(select(func.count(AccessLog.id)).where(AccessLog.user_id == uid))

    q = (
        select(AccessLog)
        .where(AccessLog.user_id == uid)
        .order_by(AccessLog.created_at.desc())
        .offset((page - 1) * ps)
        .limit(ps)
    )
    rows = db.scalars(q).all()
    lst = [
        {
            "id": r.id,
            "time": r.created_at.isoformat(),
            "createdAt": r.created_at.isoformat(),
            "success": r.success,
            "mode": r.mode,
            "abnormal": r.abnormal,
            "place": "单元门",
            "location": "单元门",
            "result": r.result,
        }
        for r in rows
    ]
    return {"list": lst, "rows": lst, "total": int(total or 0)}
