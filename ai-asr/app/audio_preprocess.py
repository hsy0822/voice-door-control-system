"""音频标准化：WAV 16kHz 单声道 16bit、降噪、首尾静音裁剪、时长与音量归一化。"""

from __future__ import annotations

import io
import logging
import re
import tempfile
from pathlib import Path
from typing import BinaryIO, Tuple, Union

import librosa
import numpy as np
import noisereduce as nr
import soundfile as sf

from app.config import MAX_DURATION_SEC, MIN_DURATION_SEC, TARGET_SR

logger = logging.getLogger(__name__)


class AudioPreprocessError(Exception):
    """预处理失败（格式、时长、空数据等）。"""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _load_audio(source: Union[bytes, BinaryIO, str, Path]) -> Tuple[np.ndarray, int]:
    """加载为 float32 波形与采样率。"""
    if isinstance(source, (bytes, bytearray)):
        y, sr = librosa.load(io.BytesIO(source), sr=None, mono=False)
    else:
        path = str(source)
        y, sr = librosa.load(path, sr=None, mono=False)

    if y.ndim == 1:
        return y.astype(np.float32), int(sr)
    # 多声道转单声道
    mono = np.mean(y, axis=0).astype(np.float32)
    return mono, int(sr)


def _resample_mono(y: np.ndarray, sr: int) -> np.ndarray:
    if sr == TARGET_SR:
        return y
    return librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR).astype(np.float32)


def _denoise(y: np.ndarray, sr: int) -> np.ndarray:
    """谱减法降噪（楼道底噪、轻微电流感）。"""
    if y.size == 0:
        return y
    try:
        reduced = nr.reduce_noise(y=y, sr=sr, stationary=True, prop_decrease=0.85)
        return reduced.astype(np.float32)
    except Exception as e:  # noqa: BLE001
        logger.warning("降噪失败，使用原波形: %s", e)
        return y


def _trim_silence(y: np.ndarray, sr: int, top_db: float = 30.0) -> np.ndarray:
    yt, _ = librosa.effects.trim(y, top_db=top_db)
    return yt.astype(np.float32)


def _peak_normalize(y: np.ndarray, peak: float = 0.98) -> np.ndarray:
    """峰值归一化，避免设备音量差异过大。"""
    if y.size == 0:
        return y
    m = float(np.max(np.abs(y)))
    if m < 1e-8:
        return y
    return (y / m * peak).astype(np.float32)


def _duration_sec(y: np.ndarray, sr: int) -> float:
    return float(len(y)) / float(sr) if sr else 0.0


def preprocess_to_wav_pcm16(
    source: Union[bytes, BinaryIO, str, Path],
    *,
    skip_denoise: bool = False,
) -> Tuple[bytes, dict]:
    """
    将任意常见音频输入转为标准 WAV（16kHz / mono / PCM_16）字节流。

    Returns:
        wav_bytes, meta dict（含 duration_sec 等）
    """
    try:
        y, sr = _load_audio(source)
    except Exception as e:  # noqa: BLE001
        raise AudioPreprocessError("AUDIO_LOAD_FAILED", f"无法解析音频: {e}") from e

    if y.size == 0:
        raise AudioPreprocessError("AUDIO_EMPTY", "无有效音频数据")

    y = _resample_mono(y, sr)
    sr = TARGET_SR

    if not skip_denoise:
        y = _denoise(y, sr)

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
    # float32 [-1,1] -> int16 PCM
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


def write_temp_bytes(
    data: bytes, directory: Path, *, suffix: str = ".bin", prefix: str = "asr_"
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=str(directory))
    Path(name).write_bytes(data)
    import os as _os

    _os.close(fd)
    return Path(name)


def write_temp_wav(wav_bytes: bytes, directory: Path, prefix: str = "asr_") -> Path:
    return write_temp_bytes(wav_bytes, directory, suffix=".wav", prefix=prefix)


def safe_filename(name: str) -> str:
    base = Path(name).name
    return re.sub(r"[^a-zA-Z0-9._-]", "_", base)[:128] or "upload.bin"
