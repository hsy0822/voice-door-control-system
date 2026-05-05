"""AI-ASR 独立 HTTP 服务：预处理 + Whisper + 认知校验。"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.asr_pipeline import (
    effective_engine,
    preload_asr,
    transcribe_wav_path,
    unload_asr,
)
from app.audio_preprocess import (
    AudioPreprocessError,
    preprocess_to_wav_pcm16,
    safe_filename,
    write_temp_bytes,
    write_temp_wav,
)
from app.cognitive import validate_answer
from app import config
from app.config import (
    LOG_DIR,
    MAX_CONCURRENT_TRANSCRIBE,
    MAX_UPLOAD_BYTES,
    TEMP_DIR,
)
from app.logging_setup import setup_logging
from app.schemas import HealthResponse, VerifyResponse

setup_logging()
logger = logging.getLogger(__name__)

_transcribe_sem = asyncio.Semaphore(MAX_CONCURRENT_TRANSCRIBE)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        preload_asr()
        logger.info(
            "AI-ASR v%s 启动，ASR=%s whisper=%s funasr=%s",
            __version__,
            effective_engine(),
            config.WHISPER_MODEL_NAME,
            config.FUNASR_MODEL,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("模型预加载失败: %s", e)
    yield
    unload_asr()
    logger.info("AI-ASR 关闭")


app = FastAPI(title="AI-ASR", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        service="ai-asr",
        whisper_model=config.WHISPER_MODEL_NAME,
        asr_engine=effective_engine(),
        funasr_model=config.FUNASR_MODEL if effective_engine() == "funasr" else None,
    )


@app.post("/api/v1/verify", response_model=VerifyResponse)
async def verify(
    audio: UploadFile = File(..., description="原始录音（建议 wav/webm/mp3 等）"),
    question: str = Form(..., description="后端下发的动态认知题目"),
) -> VerifyResponse:
    """
    接收音频 + 题目，返回识别文本与是否回答正确。
    """
    t0 = time.time()
    detail: list[str] = []
    meta: dict = {}

    raw_name = safe_filename(audio.filename or "upload")
    body = await audio.read()
    if not body:
        return VerifyResponse(
            status="AUDIO_EMPTY",
            message="上传文件为空",
            detail_log=["empty upload"],
        )
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件过大")

    tmp_in: Path | None = None
    tmp_wav: Path | None = None
    try:
        ext = Path(raw_name).suffix.lower() or ".bin"
        if ext not in (".wav", ".flac", ".mp3", ".ogg", ".webm", ".m4a", ".aac", ".bin"):
            ext = ".bin"
        tmp_in = write_temp_bytes(
            body, TEMP_DIR, suffix=ext, prefix=f"in_{uuid.uuid4().hex}_"
        )
        detail.append(f"saved_input={tmp_in.name}")

        try:
            wav_bytes, meta = preprocess_to_wav_pcm16(tmp_in)
        except AudioPreprocessError as e:
            logger.info("预处理失败 %s: %s", e.code, e)
            return VerifyResponse(
                status=e.code,
                message=str(e),
                audio_meta=meta,
                detail_log=detail + [e.code],
            )

        tmp_wav = write_temp_wav(wav_bytes, TEMP_DIR, prefix=f"std_{uuid.uuid4().hex}_")
        detail.append(f"standard_wav={tmp_wav.name}")

        async with _transcribe_sem:
            recognized, whisper_info = await asyncio.to_thread(
                transcribe_wav_path, tmp_wav, question
            )

        if whisper_info.get("error"):
            return VerifyResponse(
                status="ASR_FAILED",
                message="识别阶段失败",
                audio_meta=meta,
                detail_log=detail + [str(whisper_info)],
            )

        if not recognized:
            vr = validate_answer(question, "")
            log_line = (
                f"time={time.time():.3f} elapsed={time.time()-t0:.3f} "
                f"question={question!r} text= empty correct=False type={vr.question_type}"
            )
            logger.info(log_line)
            return VerifyResponse(
                status="NO_SPEECH",
                recognized_text="",
                answer_correct=False,
                question_type=vr.question_type,
                expected_answer=vr.expected_display,
                message="未检测到有效语音内容",
                audio_meta=meta,
                detail_log=detail + ["empty transcript"],
            )

        vr = validate_answer(question, recognized)
        ok = vr.correct
        log_line = (
            f"time={time.time():.3f} elapsed={time.time()-t0:.3f} "
            f"question={question!r} text={recognized!r} correct={ok} "
            f"type={vr.question_type} reason={vr.reason}"
        )
        logger.info(log_line)

        return VerifyResponse(
            status="success",
            recognized_text=recognized,
            answer_correct=ok,
            question_type=vr.question_type,
            expected_answer=vr.expected_display,
            message=vr.reason,
            audio_meta=meta,
            detail_log=detail,
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("verify 未捕获异常: %s", e)
        return VerifyResponse(
            status="INTERNAL_ERROR",
            message=f"服务内部错误: {e}",
            audio_meta=meta,
            detail_log=detail + ["exception"],
        )
    finally:
        for p in (tmp_in, tmp_wav):
            if p and p.is_file():
                try:
                    p.unlink()
                except OSError:
                    pass
