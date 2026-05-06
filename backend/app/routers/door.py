"""动态题、三轨鉴权、访客开门。"""

from __future__ import annotations

import asyncio
import datetime as dt
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import ResidentUser
from app.models import AccessLog, AlarmLog, Challenge, User, VisitorAuth
from app.services.ai_client import call_asr, call_emotion, call_voiceprint
from app.services.cognitive_bank import normalize_q, pick_question

router = APIRouter(prefix="/door", tags=["door"])


@router.get("/challenge")
def door_challenge(
    user: ResidentUser,
    db: Session = Depends(get_db),
) -> dict:
    if not user.door_enabled:
        raise HTTPException(status_code=403, detail="门禁权限已停用")
    recent = db.scalars(
        select(Challenge.question)
        .where(Challenge.user_id == user.id)
        .order_by(Challenge.created_at.desc())
        .limit(8)
    ).all()
    q = pick_question(list(recent))
    cid = uuid.uuid4().hex
    db.add(
        Challenge(
            id=cid,
            user_id=user.id,
            question=q.strip(),
            used=False,
        )
    )
    db.commit()
    return {"question": q, "challengeId": cid}


async def _tri_track(
    user_id: int,
    audio: bytes,
    filename: str,
    question: str,
) -> tuple[dict, dict, dict]:
    timeout = httpx.Timeout(settings.ai_http_timeout_sec)
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await asyncio.gather(
            call_asr(client, audio, filename, question),
            call_voiceprint(client, user_id, audio, filename),
            call_emotion(client, user_id, audio, filename),
        )


@router.post("/verify")
async def door_verify(
    user: ResidentUser,
    db: Session = Depends(get_db),
    userId: str = Form(...),
    challengeId: str = Form(""),
    passphrase: str = Form(...),
    audio: UploadFile = File(...),
) -> dict:
    if not user.door_enabled:
        raise HTTPException(status_code=403, detail="门禁权限已停用")
    try:
        uid = int(userId)
    except ValueError:
        raise HTTPException(status_code=400, detail="用户 ID 无效")
    if uid != user.id:
        raise HTTPException(status_code=403, detail="身份不一致")
    if not challengeId.strip():
        raise HTTPException(status_code=400, detail="缺少 challengeId")

    ch = db.get(Challenge, challengeId.strip())
    if not ch or ch.user_id != user.id or ch.used:
        raise HTTPException(status_code=400, detail="口令会话无效或已使用，请刷新题目")
    if normalize_q(ch.question) != normalize_q(passphrase):
        raise HTTPException(status_code=400, detail="题目与会话不匹配")

    body = await audio.read()
    if not body:
        raise HTTPException(status_code=400, detail="音频为空")
    fname = audio.filename or "answer.wav"

    asr_r, voice_r, emo_r = await _tri_track(user.id, body, fname, ch.question.strip())
    ch.used = True

    def _log(
        success: bool,
        result: str,
        abnormal: bool,
        detail: Optional[str] = None,
    ) -> None:
        db.add(
            AccessLog(
                user_id=user.id,
                username=user.username,
                mode="self",
                success=success,
                result=result,
                abnormal=abnormal,
                detail=detail,
            )
        )

    if not asr_r.get("ok"):
        _log(False, "口令/认知未通过", False, asr_r.get("error"))
        db.commit()
        return {
            "success": False,
            "failType": "passphrase",
            "reason": asr_r.get("error") or "口令验证失败",
        }

    if not voice_r.get("ok"):
        _log(False, "声纹未通过", False, voice_r.get("error"))
        db.commit()
        return {
            "success": False,
            "failType": "voice",
            "reason": voice_r.get("error") or "声纹不匹配",
        }

    duress = bool(emo_r.get("duress"))
    emotion = str(emo_r.get("emotion") or "")

    if duress:
        _log(True, "开门成功", True, f"胁迫静默: emotion={emotion}")
        db.add(
            AlarmLog(
                user_id=user.id,
                emotion=emotion or "coercion",
                detail="胁迫状态下开门（静默告警）",
                resolved=False,
            )
        )
        db.commit()
        return {
            "success": True,
            "duress": True,
            "coercion": True,
            "emotion": emotion or "coercion",
        }

    _log(True, "开门成功", False, None)
    db.commit()
    return {"success": True, "duress": False, "emotion": emotion or "neutral"}


class VisitorOpenBody(BaseModel):
    token: str = Field(min_length=4, max_length=64)


@router.post("/visitor-open")
def visitor_open(body: VisitorOpenBody, db: Session = Depends(get_db)) -> dict:
    """访客凭临时口令开门（无需登录）。"""
    raw = body.token.strip().upper()
    row = db.scalar(select(VisitorAuth).where(VisitorAuth.token == raw))
    now = dt.datetime.now(dt.timezone.utc)

    def _fail(result: str, reason: str, creator_id: Optional[int] = None) -> dict:
        db.add(
            AccessLog(
                user_id=creator_id,
                username="访客",
                mode="visitor",
                success=False,
                result=result,
                abnormal=False,
                detail=None,
            )
        )
        db.commit()
        return {"success": False, "reason": reason}

    if not row:
        return _fail("口令无效", "口令无效", None)

    if row.expires_at is not None and row.expires_at < now:
        return _fail("口令已过期", "口令已过期", row.creator_user_id)

    if row.auth_type == "once" and row.used:
        return _fail("口令已使用", "口令已使用", row.creator_user_id)

    if row.auth_type == "once":
        row.used = True

    creator = db.get(User, row.creator_user_id)
    uname = creator.username if creator else ""
    db.add(
        AccessLog(
            user_id=row.creator_user_id,
            username=f"访客→{uname}",
            mode="visitor",
            success=True,
            result="访客开门成功",
            abnormal=False,
            detail=f"token_id={row.id}",
        )
    )
    db.commit()
    return {"success": True}
