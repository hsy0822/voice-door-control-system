"""声纹（VPR）+ 情感（SER）FastAPI 子服务，默认端口 8002。"""

from __future__ import annotations

import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app import config, engine
from app.audio_preprocess import AudioPreprocessError, preprocess_to_wav_pcm16

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def _safe_name(name: str) -> str:
    base = Path(name).name
    return re.sub(r"[^a-zA-Z0-9._-]", "_", base)[:128] or "upload.bin"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    for d in (config.DATA_DIR, config.MODELS_DIR, config.TEMP_DIR, config.LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if os.environ.get("VPR_SER_PRELOAD", "1").strip().lower() not in ("0", "false", "no", "off"):
        try:
            engine.preload_models()
            logger.info("模型预加载完成 device=%s", engine._device())
        except Exception as e:  # noqa: BLE001
            logger.exception("模型预加载失败（首次请求时会再尝试）: %s", e)
    yield


app = FastAPI(
    title="ai-vpr-ser",
    version=__version__,
    description="声纹识别（VPR）与情感胁迫检测（SER），供后端三轨并发调用。",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def _http_exc(_request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    msg = detail if isinstance(detail, str) else str(detail)
    return JSONResponse(status_code=exc.status_code, content={"message": msg})


def _write_preprocessed_wav(raw: bytes, suffix: str) -> Path:
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件过大")
    try:
        wav_bytes, _meta = preprocess_to_wav_pcm16(raw)
    except AudioPreprocessError as e:
        raise HTTPException(status_code=400, detail=f"{e.code}: {e}") from e
    p = config.TEMP_DIR / f"{uuid.uuid4().hex}{suffix}"
    p.write_bytes(wav_bytes)
    return p


@app.get("/api/v1/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "ai-vpr-ser",
        "version": __version__,
        "device": engine._device(),
    }


@app.get("/api/v1/status")
def status() -> dict:
    spk_ok = engine.speaker_model_ready()
    emo_ok = engine.emotion_model_ready()
    return {
        "ok": True,
        "speaker_model_loaded": spk_ok,
        "emotion_model_loaded": emo_ok,
        "spkrec_source": config.SPKREC_SOURCE,
        "emotion_source": config.EMOTION_SOURCE,
        "voice_threshold": config.VOICE_MATCH_THRESHOLD,
        "voiceprints_root_configured": bool(config.VOICEPRINTS_ROOT),
    }


@app.post("/api/v1/voice/enroll")
async def voice_enroll(
    user_id: str = Form(..., description="用户 ID，与后端一致"),
    segment1: UploadFile = File(...),
    segment2: UploadFile = File(...),
    segment3: UploadFile = File(...),
) -> dict:
    uid = str(user_id).strip()
    if not uid:
        raise HTTPException(status_code=400, detail="user_id 无效")
    paths: list[Path] = []
    try:
        for uf in (segment1, segment2, segment3):
            body = await uf.read()
            if not body:
                raise HTTPException(status_code=400, detail="存在空录音")
            paths.append(_write_preprocessed_wav(body, f"_{_safe_name(uf.filename)}.wav"))
        outp = engine.enroll_three_segments(uid, paths)
        return {
            "success": True,
            "user_id": uid,
            "enrollment_path": str(outp),
            "message": "声纹注册成功",
        }
    finally:
        for p in paths:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass


@app.post("/api/v1/voice/verify")
async def voice_verify(
    user_id: str = Form(...),
    audio: UploadFile = File(...),
) -> dict:
    """供后端解析：match / success / ok 任一为真即通过。"""
    uid = str(user_id).strip()
    body = await audio.read()
    if not body:
        raise HTTPException(status_code=400, detail="音频为空")
    tmp: Path | None = None
    try:
        tmp = _write_preprocessed_wav(body, f"_{_safe_name(audio.filename)}.wav")
        ok, score, msg = engine.verify_voice(uid, tmp)
        return {
            "match": ok,
            "success": ok,
            "ok": ok,
            "score": round(score, 4),
            "message": msg,
        }
    finally:
        if tmp:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass


@app.post("/api/v1/emotion/analyze")
async def emotion_analyze(
    audio: UploadFile = File(...),
    user_id: str = Form("", description="可选，仅占位与后端字段对齐"),
) -> dict:
    body = await audio.read()
    if not body:
        raise HTTPException(status_code=400, detail="音频为空")
    tmp: Path | None = None
    try:
        tmp = _write_preprocessed_wav(body, f"_{_safe_name(audio.filename)}.wav")
        out = engine.classify_emotion(tmp)
        return {
            "emotion": out["emotion"],
            "label": out["emotion"],
            "confidence": out["confidence"],
            "duress": out["duress"],
            "coercion": out["coercion"],
            "detail": out.get("label_raw"),
        }
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("情感推理失败: %s", e)
        raise HTTPException(status_code=500, detail=f"情感推理失败: {e}") from e
    finally:
        if tmp:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
