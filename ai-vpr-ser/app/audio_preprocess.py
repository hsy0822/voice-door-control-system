"""
音频预处理：与 ai-asr 门禁标准对齐（16 kHz / mono / PCM16、静音裁剪、峰值归一化、时长约束）。

不强制依赖 noisereduce（与 ASR 全量预处理略有差异，但采样率与位深一致，便于三轨共用录音）。

注意：本服务与 SpeechBrain 共存于同一进程，librosa.load() 会触发 SB 的 LazyModule 冲突，
因此音频加载与重采样改用 soundfile + scipy，避开 librosa。
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import BinaryIO, Tuple, Union

import numpy as np
import soundfile as sf

from app.config import MAX_DURATION_SEC, MIN_DURATION_SEC, TARGET_SR

logger = logging.getLogger(__name__)


class AudioPreprocessError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _load_audio(source: Union[bytes, BinaryIO, str, Path]) -> Tuple[np.ndarray, int]:
    """
    用 soundfile 加载音频（不用 librosa，避免触发 SpeechBrain LazyModule 冲突）。
    返回 (mono_float32, sample_rate)。
    """
    try:
        if isinstance(source, (bytes, bytearray)):
            y, sr = sf.read(io.BytesIO(source), dtype="float32")
        else:
            y, sr = sf.read(str(source), dtype="float32")
    except Exception as e:
        raise AudioPreprocessError("AUDIO_LOAD_FAILED", f"soundfile 无法解析音频: {e}") from e

    # 多声道转单声道
    if y.ndim > 1:
        y = np.mean(y, axis=1).astype(np.float32)

    return y, int(sr)


def _resample_mono(y: np.ndarray, sr: int) -> np.ndarray:
    """用 scipy 重采样（不用 librosa.resample，避开 LazyModule 冲突）。"""
    if sr == TARGET_SR:
        return y
    try:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(TARGET_SR, sr)
        up = TARGET_SR // g
        down = sr // g
        y_out = resample_poly(y, up, down).astype(np.float32)
        return y_out
    except ImportError:
        # scipy 不可用时，用简单线性插值兜底
        ratio = TARGET_SR / sr
        n_out = int(len(y) * ratio)
        indices = np.linspace(0, len(y) - 1, n_out)
        y_out = np.interp(indices, np.arange(len(y)), y).astype(np.float32)
        return y_out


def _trim_silence(y: np.ndarray, sr: int, top_db: float = 30.0) -> np.ndarray:
    """
    简易静音裁剪（不用 librosa.effects.trim，避开 LazyModule 冲突）。
    基于 RMS 能量窗口检测有效语音区间。
    """
    frame_len = int(sr * 0.025)  # 25ms 帧
    hop_len = int(sr * 0.010)    # 10ms 步长
    if len(y) < frame_len:
        return y

    # 计算 RMS 能量
    n_frames = 1 + (len(y) - frame_len) // hop_len
    energy = np.zeros(n_frames, dtype=np.float32)
    for i in range(n_frames):
        start = i * hop_len
        frame = y[start:start + frame_len]
        energy[i] = np.sqrt(np.mean(frame ** 2))

    if energy.max() < 1e-8:
        return y

    # 阈值：最大能量 - top_db dB
    db_max = 20.0 * np.log10(energy.max() + 1e-10)
    db_threshold = db_max - top_db
    db_energy = 20.0 * np.log10(energy + 1e-10)

    # 找到第一个和最后一个超过阈值的帧
    above = np.where(db_energy >= db_threshold)[0]
    if len(above) == 0:
        return y

    first_frame = above[0]
    last_frame = above[-1]

    start_sample = first_frame * hop_len
    end_sample = min((last_frame + 1) * hop_len + frame_len, len(y))

    return y[start_sample:end_sample].astype(np.float32)


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
    except AudioPreprocessError:
        raise
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
