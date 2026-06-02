"""
本地 Whisper 冒烟测试（需已安装 openai-whisper，首次会下载权重）。

推荐从 ai-asr 目录执行：
  python test_asr.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import whisper


def main() -> None:
    sr = 16000
    t = np.linspace(0, 1.5, int(sr * 1.5), endpoint=False)
    y = 0.05 * np.sin(2 * np.pi * 200 * t).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = Path(f.name)
    try:
        sf.write(path, y, sr, subtype="PCM_16")
        model = whisper.load_model("tiny")
        r = model.transcribe(
            str(path), language="zh", fp16=False, verbose=False, temperature=0.0
        )
        print("Whisper tiny 推理完成，原始文本:", (r.get("text") or "").strip())
    finally:
        if path.is_file():
            path.unlink()


if __name__ == "__main__":
    main()
