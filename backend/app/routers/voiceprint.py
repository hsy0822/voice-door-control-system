"""声纹录入提示与提交。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import ResidentUser
from app.models import VoicePrint
from app.services.ai_client import save_voiceprint_segments
from app.services.voiceprint_prompts import pick_three

router = APIRouter(prefix="/voiceprint", tags=["voiceprint"])


@router.get("/prompts")
def voiceprint_prompts() -> dict:
    return {"segments": pick_three()}


@router.post("/submit")
async def voiceprint_submit(
    user: ResidentUser,
    db: Session = Depends(get_db),
    userId: str = Form(...),
    segment1: UploadFile = File(...),
    segment2: UploadFile = File(...),
    segment3: UploadFile = File(...),
) -> dict:
    try:
        uid = int(userId)
    except ValueError:
        raise HTTPException(status_code=400, detail="用户 ID 无效")
    if uid != user.id:
        raise HTTPException(status_code=403, detail="身份不一致")

    blobs: list[tuple[bytes, str]] = []
    for uf in (segment1, segment2, segment3):
        b = await uf.read()
        if not b:
            raise HTTPException(status_code=400, detail="存在空录音文件")
        blobs.append((b, uf.filename or "seg.wav"))

    path_json = save_voiceprint_segments(user.id, blobs)
    db.execute(delete(VoicePrint).where(VoicePrint.user_id == user.id))
    db.flush()
    db.add(VoicePrint(user_id=user.id, feature_path=path_json))
    db.commit()
    return {"success": True, "message": "声纹已保存"}
