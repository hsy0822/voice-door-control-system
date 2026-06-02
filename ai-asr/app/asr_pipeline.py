"""ASR 引擎调度：默认 FunASR（路线 C），可切回 Whisper；FunASR 不可用时自动回退 Whisper。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

from app import config

logger = logging.getLogger(__name__)

_runtime_engine: Optional[str] = None


def effective_engine() -> str:
    """实际使用的引擎（预加载后确定，可能因回退与 ASR_ENGINE 不同）。"""
    return _runtime_engine or config.ASR_ENGINE


def preload_asr() -> None:
    """启动时预加载，避免首请求过慢。"""
    global _runtime_engine
    _runtime_engine = None
    want = (config.ASR_ENGINE or "funasr").strip().lower()
    if want == "funasr":
        try:
            from app.asr_funasr import get_funasr_model

            get_funasr_model()
            _runtime_engine = "funasr"
            logger.info("ASR 引擎: FunASR (%s)", config.FUNASR_MODEL)
            return
        except Exception as e:  # noqa: BLE001
            logger.warning("FunASR 预加载失败，改用 Whisper: %s", e)

    from app.asr_whisper import get_model

    get_model()
    _runtime_engine = "whisper"
    logger.info("ASR 引擎: Whisper (%s)", config.WHISPER_MODEL_NAME)


def unload_asr() -> None:
    from app import asr_funasr
    from app import asr_whisper

    asr_funasr.unload_funasr()
    asr_whisper.unload_model()
    global _runtime_engine
    _runtime_engine = None


def transcribe_wav_path(
    wav_path: str | Path, question: Optional[str] = None
) -> Tuple[str, dict]:
    eng = effective_engine()
    if eng == "funasr":
        try:
            from app.asr_funasr import transcribe_funasr

            return transcribe_funasr(wav_path, question=question)
        except Exception as e:  # noqa: BLE001
            logger.warning("FunASR 推理失败，本次回退 Whisper: %s", e)
    from app.asr_whisper import transcribe_wav_path as whisper_transcribe

    text, info = whisper_transcribe(wav_path, question=question)
    info.setdefault("engine", "whisper")
    if eng == "funasr":
        info["fallback_from_funasr"] = True
    return text, info
