"""管理员统计、日志、告警、住户。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import AdminUser
from app.models import AccessLog, AlarmLog, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def admin_stats(
    _admin: AdminUser,
    db: Session = Depends(get_db),
) -> dict:
    total_opens = db.scalar(
        select(func.count(AccessLog.id)).where(AccessLog.success.is_(True))
    )
    alarm_count = db.scalar(
        select(func.count(AlarmLog.id)).where(AlarmLog.resolved.is_(False))
    )
    return {
        "totalOpens": int(total_opens or 0),
        "openCount": int(total_opens or 0),
        "alarmCount": int(alarm_count or 0),
        "abnormalCount": int(alarm_count or 0),
    }


@router.get("/logs/door")
def admin_door_logs(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    page: int = 1,
    pageSize: int = 20,
) -> dict:
    page = max(1, page)
    ps = min(100, max(1, pageSize))
    q = (
        select(AccessLog)
        .order_by(AccessLog.created_at.desc())
        .offset((page - 1) * ps)
        .limit(ps)
    )
    rows = db.scalars(q).all()
    lst = []
    for r in rows:
        lst.append(
            {
                "id": r.id,
                "time": r.created_at.isoformat(),
                "createdAt": r.created_at.isoformat(),
                "userName": r.username,
                "user": r.username,
                "success": r.success,
                "abnormal": r.abnormal,
                "result": r.result if not r.success else ("异常" if r.abnormal else "成功"),
                "place": "单元门",
                "location": "单元门",
            }
        )
    return {"list": lst, "rows": lst}


@router.get("/alarms")
def admin_alarms(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    page: int = 1,
    pageSize: int = 20,
) -> dict:
    page = max(1, page)
    ps = min(100, max(1, pageSize))
    q = (
        select(AlarmLog)
        .order_by(AlarmLog.created_at.desc())
        .offset((page - 1) * ps)
        .limit(ps)
    )
    rows = db.scalars(q).all()
    lst = []
    for r in rows:
        uname = ""
        if r.user_id:
            u = db.get(User, r.user_id)
            uname = u.username if u else ""
        lst.append(
            {
                "id": r.id,
                "userName": uname,
                "user": uname,
                "emotion": r.emotion,
                "time": r.created_at.isoformat(),
                "createdAt": r.created_at.isoformat(),
                "resolved": r.resolved,
                "place": "单元门",
                "location": "单元门",
                "detail": r.detail or "",
                "description": r.detail or "",
            }
        )
    return {"list": lst, "rows": lst}


@router.post("/alarms/{alarm_id}/resolve")
def resolve_alarm(
    alarm_id: int,
    _admin: AdminUser,
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(AlarmLog, alarm_id)
    if not row:
        raise HTTPException(status_code=404, detail="告警不存在")
    row.resolved = True
    db.commit()
    return {"success": True}


@router.get("/residents")
def list_residents(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    page: int = 1,
    pageSize: int = 20,
) -> dict:
    page = max(1, page)
    ps = min(100, max(1, pageSize))
    q = (
        select(User)
        .where(User.role == "resident")
        .order_by(User.created_at.desc())
        .offset((page - 1) * ps)
        .limit(ps)
    )
    rows = db.scalars(q).all()
    lst = [
        {
            "id": r.id,
            "username": r.username,
            "name": r.username,
            "doorAuth": r.door_enabled and r.status == "active",
        }
        for r in rows
    ]
    return {"list": lst, "rows": lst}


class DoorAuthBody(BaseModel):
    doorAuth: bool


@router.put("/residents/{resident_id}/door-auth")
def set_resident_door_auth(
    resident_id: int,
    body: DoorAuthBody,
    _admin: AdminUser,
    db: Session = Depends(get_db),
) -> dict:
    u = db.get(User, resident_id)
    if not u or u.role != "resident":
        raise HTTPException(status_code=404, detail="住户不存在")
    u.door_enabled = body.doorAuth
    db.commit()
    return {"success": True, "doorAuth": u.door_enabled}
