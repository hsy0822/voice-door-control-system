"""FunASR（Paraformer 等）中文 ASR — 适合短句、数字场景，无需自建训练集。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Tuple

from app.asr_text import clean_chinese_text, filter_arithmetic_single_garbage
from app.config import ASR_DEVICE, FUNASR_MODEL

logger = logging.getLogger(__name__)

_model: Any = None


def _text_from_result(res: Any) -> str:
    if not res:
        return ""
    first = res[0] if isinstance(res, (list, tuple)) else res
    if isinstance(first, dict):
        return str(first.get("text") or "").strip()
    if isinstance(first, str):
        return first.strip()
    return ""


def get_funasr_model() -> Any:
    global _model
    if _model is None:
        try:
            from funasr import AutoModel
        except ImportError as e:  # noqa: PERF203
            raise RuntimeError(
                "未安装 funasr，请执行: pip install funasr modelscope"
            ) from e
        logger.info("加载 FunASR 模型: %s device=%s", FUNASR_MODEL, ASR_DEVICE)
        _model = AutoModel(
            model=FUNASR_MODEL,
            device=ASR_DEVICE,
            disable_update=True,
        )
    return _model


def unload_funasr() -> None:
    global _model
    _model = None


def transcribe_funasr(
    wav_path: str | Path, question: Optional[str] = None
) -> Tuple[str, dict]:
    """
    对 16kHz 单声道 WAV 做识别。question 当前仅参与后处理，不参与 FunASR 解码。
    """
    path = Path(wav_path)
    if not path.is_file():
        return "", {"error": "file_not_found", "engine": "funasr"}

    model = get_funasr_model()
    res = model.generate(input=str(path))
    raw = _text_from_result(res)
    cleaned = clean_chinese_text(raw)
    cleaned, hallu = filter_arithmetic_single_garbage(cleaned, question)

    info: dict = {
        "raw_text": raw,
        "segments": [],
        "engine": "funasr",
        "funasr_model": FUNASR_MODEL,
    }
    if hallu:
        info["hallucination_filtered"] = True
    return cleaned, info
