"""预处理单元测试（不加载 Whisper）。"""

import pytest
import numpy as np
import soundfile as sf

from app.audio_preprocess import AudioPreprocessError, preprocess_to_wav_pcm16


def _bytes_wav_from_float(y: np.ndarray, sr: int) -> bytes:
    import io

    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def test_standardize_mono_48k_to_16k() -> None:
    sr = 48000
    t = np.linspace(0, 2.0, int(sr * 2), endpoint=False)
    y = 0.1 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    raw = _bytes_wav_from_float(y, sr)
    wav, meta = preprocess_to_wav_pcm16(raw, skip_denoise=True)
    assert meta["sample_rate"] == 16000
    assert meta["channels"] == 1
    assert 1.0 <= meta["duration_sec"] <= 5.0
    assert len(wav) > 1000


def test_too_short_after_trim_raises() -> None:
    sr = 16000
    # 几乎全静音，trim 后极短
    y = (np.random.randn(int(sr * 0.2)) * 1e-5).astype(np.float32)
    raw = _bytes_wav_from_float(y, sr)
    with pytest.raises(AudioPreprocessError) as e:
        preprocess_to_wav_pcm16(raw, skip_denoise=True)
    assert e.value.code == "AUDIO_TOO_SHORT"
