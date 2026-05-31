"""声纹录入提示与提交。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import ResidentUser
from app.models import VoicePrint
from app.services.ai_client import call_voice_enroll, save_voiceprint_segments
from app.services.voiceprint_prompts import pick_three

router = APIRouter(prefix="/voiceprint", tags=["voiceprint"])


@router.get("/prompts")
def voiceprint_prompts() -> dict:
    return {"segments": pick_three()}


@router.get("/status")
def voiceprint_status(user: ResidentUser, db: Session = Depends(get_db)) -> dict:
    """是否已录入：数据库记录 + 磁盘三段 wav；门禁是否走真实声纹取决于 VOICE_VERIFY_URL 等配置。"""
    row = db.scalar(select(VoicePrint).where(VoicePrint.user_id == user.id))
    base = settings.data_dir / "voiceprints" / str(user.id)
    segs = {f"seg{i}": (base / f"seg{i}.wav").is_file() for i in (1, 2, 3)}
    url_ok = bool(settings.voice_verify_url.strip())
    return {
        "saved_in_database": row is not None,
        "segment_files": segs,
        "all_segments_present": all(segs.values()),
        "voice_verify_url_configured": url_ok,
        "segments_stub_enabled": bool(settings.voice_verify_allow_segments_stub),
        "mock_voiceprint_match": bool(settings.mock_voiceprint_match),
        "ready_for_real_verify": url_ok
        and all(segs.values())
        and not settings.mock_voiceprint_match
        and not settings.voice_verify_allow_segments_stub,
    }


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

    # 1) 保存原始 WAV 到磁盘（保留原有逻辑）
    path_json = save_voiceprint_segments(user.id, blobs)

    # 2) 调用声纹服务注册特征向量（核心修复！）
    enroll_result = await call_voice_enroll(user.id, blobs)
    if not enroll_result.get("ok"):
        # 注册失败只打日志，不阻断录入（WAV 已保存，可后续补注册）
        import logging
        logging.getLogger(__name__).warning(
            "声纹特征注册失败（WAV 已保存）: %s", enroll_result.get("error")
        )

    # 3) 更新数据库
    db.execute(delete(VoicePrint).where(VoicePrint.user_id == user.id))
    db.flush()
    db.add(VoicePrint(user_id=user.id, feature_path=path_json))
    db.commit()

    return {
        "success": True,
        "message": "声纹已保存",
        "enrolled": enroll_result.get("ok", False),
    }
