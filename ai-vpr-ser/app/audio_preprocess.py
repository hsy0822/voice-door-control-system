"""
音频预处理：与 ai-asr 门禁标准对齐（16 kHz / mono / PCM16、静音裁剪、峰值归一化、时长约束）。

不强制依赖 noisereduce（与 ASR 全量预处理略有差异，但采样率与位深一致，便于三轨共用录音）。
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import BinaryIO, Tuple, Union

import librosa
import numpy as np
import soundfile as sf

from app.config import MAX_DURATION_SEC, MIN_DURATION_SEC, TARGET_SR

logger = logging.getLogger(__name__)


class AudioPreprocessError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _load_audio(source: Union[bytes, BinaryIO, str, Path]) -> Tuple[np.ndarray, int]:
    if isinstance(source, (bytes, bytearray)):
        y, sr = librosa.load(io.BytesIO(source), sr=None, mono=False)
    else:
        y, sr = librosa.load(str(source), sr=None, mono=False)
    if y.ndim == 1:
        return y.astype(np.float32), int(sr)
    return np.mean(y, axis=0).astype(np.float32), int(sr)


def _resample_mono(y: np.ndarray, sr: int) -> np.ndarray:
    if sr == TARGET_SR:
        return y
    return librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR).astype(np.float32)


def _trim_silence(y: np.ndarray, sr: int, top_db: float = 30.0) -> np.ndarray:
    yt, _ = librosa.effects.trim(y, top_db=top_db)
    return yt.astype(np.float32)


def _peak_normalize(y: np.ndarray, peak: float = 0.98) -> np.ndarray:
    if y.size == 0:
        return y
    m = float(np.max(np.abs(y)))
    if m < 1e-8:
        return y
    return (y / m * peak).astype(np.float32)


def _duration_sec(y: np.ndarray, sr: int) -> float:
    return float(len(y)) / float(sr) if sr else 0.0


def preprocess_to_wav_pcm16(source: Union[bytes, BinaryIO, str, Path]) -> Tuple[bytes, dict]:
    try:
        y, sr = _load_audio(source)
    except Exception as e:  # noqa: BLE001
        raise AudioPreprocessError("AUDIO_LOAD_FAILED", f"无法解析音频: {e}") from e
    if y.size == 0:
        raise AudioPreprocessError("AUDIO_EMPTY", "无有效音频数据")
    y = _resample_mono(y, sr)
    sr = TARGET_SR
    y = _trim_silence(y, sr)
    dur = _duration_sec(y, sr)
    if dur < MIN_DURATION_SEC:
        raise AudioPreprocessError(
            "AUDIO_TOO_SHORT",
            f"有效时长 {dur:.2f}s 小于 {MIN_DURATION_SEC}s",
        )
    if dur > MAX_DURATION_SEC:
        raise AudioPreprocessError(
            "AUDIO_TOO_LONG",
            f"有效时长 {dur:.2f}s 超过 {MAX_DURATION_SEC}s",
        )
    y = _peak_normalize(y)
    y_i16 = (np.clip(y, -1.0, 1.0) * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    sf.write(buf, y_i16, sr, format="WAV", subtype="PCM_16")
    wav_bytes = buf.getvalue()
    meta = {
        "duration_sec": round(dur, 3),
        "sample_rate": sr,
        "channels": 1,
        "format": "WAV",
        "subtype": "PCM_16",
    }
    return wav_bytes, meta
