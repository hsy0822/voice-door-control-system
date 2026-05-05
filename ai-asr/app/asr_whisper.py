"""OpenAI Whisper 推理（中文）；由 asr_pipeline 按需调用。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import librosa
import numpy as np
import soundfile as sf
import whisper

from app.asr_text import clean_chinese_text, filter_arithmetic_single_garbage
from app.cognitive import whisper_context_prompt
from app.config import WHISPER_MODEL_NAME

logger = logging.getLogger(__name__)

_model: Optional[whisper.Whisper] = None


def get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        logger.info("加载 Whisper 模型: %s", WHISPER_MODEL_NAME)
        _model = whisper.load_model(WHISPER_MODEL_NAME)
    return _model


def unload_model() -> None:
    global _model
    _model = None


def _looks_like_initial_prompt_echo(text: str) -> bool:
    """
    Whisper 在短音频 + initial_prompt 时，可能把提示里的顿号列举复读进正文。
    """
    if len(text) < 24:
        return False
    if text.count("、") >= 8:
        return True
    for win in (6, 8, 10, 12):
        if len(text) < win * 3:
            continue
        chunk = text[:win]
        if chunk and text.count(chunk) >= 4:
            return True
    return False


def _load_mono_float32_16k(path: Path) -> np.ndarray:
    audio, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000).astype(np.float32)
    return audio.astype(np.float32)


def transcribe_wav_path(
    wav_path: str | Path, question: Optional[str] = None
) -> Tuple[str, dict]:
    """
    对标准 WAV（建议 16kHz 单声道）做识别，返回 (清洗后文本, 附加信息)。
    question 用于 initial_prompt 语境。
    """
    path = Path(wav_path)
    if not path.is_file():
        return "", {"error": "file_not_found", "engine": "whisper"}

    model = get_model()
    audio = _load_mono_float32_16k(path)

    ctx = whisper_context_prompt(question or "")
    initial_prompt = f"{ctx}现场录音。"

    result = model.transcribe(
        audio,
        language="zh",
        fp16=False,
        verbose=False,
        temperature=0.0,
        beam_size=5,
        best_of=1,
        condition_on_previous_text=False,
        initial_prompt=initial_prompt,
        carry_initial_prompt=False,
        without_timestamps=True,
    )
    raw = (result.get("text") or "").strip()
    cleaned = clean_chinese_text(raw)
    info: dict = {
        "raw_text": raw,
        "segments": result.get("segments") or [],
        "engine": "whisper",
    }

    if _looks_like_initial_prompt_echo(cleaned):
        logger.warning("疑似复述 initial_prompt，已丢弃转写")
        info["echo_filtered"] = True
        cleaned = ""

    cleaned, hallu = filter_arithmetic_single_garbage(cleaned, question)
    if hallu:
        logger.info("算术题下单字疑似误识，已丢弃: %r", info.get("raw_text", ""))
        info["hallucination_filtered"] = True

    return cleaned, info
