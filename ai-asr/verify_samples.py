"""对 ai-asr 目录内用户放置的 wav 跑预处理 + 识别 + 校验。

用法（在 ai-asr 目录）:
  python verify_samples.py              # 每个文件一道默认题（口算、常识各一）
  python verify_samples.py --matrix     # 每个文件都跑口算 + 常识，便于对照录音内容
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 保证可从 ai-asr 根目录执行
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.asr_pipeline import preload_asr, transcribe_wav_path  # noqa: E402
from app.audio_preprocess import (  # noqa: E402
    AudioPreprocessError,
    preprocess_to_wav_pcm16,
    write_temp_wav,
)
from app.cognitive import validate_answer  # noqa: E402
from app.config import TEMP_DIR  # noqa: E402


def _find_sample_wavs(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*.wav"):
        if ".venv" in p.parts:
            continue
        if "tests" in p.parts:
            continue
        out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def _run_one(wav: Path, question: str) -> None:
    print("\n" + "=" * 60)
    print("文件:", wav)
    print("题目:", question)
    tmp_std: Path | None = None
    try:
        try:
            wav_bytes, meta = preprocess_to_wav_pcm16(wav)
        except AudioPreprocessError as e:
            print("预处理失败:", e.code, e)
            return
        print("预处理 meta:", meta)
        tmp_std = write_temp_wav(wav_bytes, TEMP_DIR, prefix="sample_")
        text, info = transcribe_wav_path(tmp_std, question=question)
        if info.get("echo_filtered"):
            print("转写: (已过滤疑似提示词回声)")
        if info.get("hallucination_filtered"):
            print("转写: (已过滤算术单字语气误识)")
        print("原始 whisper:", repr(info.get("raw_text", "")))
        print("清洗后文本:", repr(text))
        vr = validate_answer(question, text)
        print("题型:", vr.question_type)
        print("期望展示:", vr.expected_display)
        print("是否正确:", vr.correct)
        print("说明:", vr.reason)
    finally:
        if tmp_std and tmp_std.is_file():
            try:
                tmp_std.unlink()
            except OSError:
                pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="每个 wav 对「3+5=?」与「天空是什么颜色？」各跑一遍",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    wavs = _find_sample_wavs(root)
    if not wavs:
        print("未在 ai-asr 下（排除 .venv/tests）找到 .wav 文件。")
        sys.exit(1)

    print("找到 wav:", len(wavs))
    for w in wavs:
        print(" -", w)

    print("\n预加载 ASR（FunASR 或 Whisper，首次可能下载权重）…")
    preload_asr()
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    default_questions = ["3+5=?", "天空是什么颜色？"]
    if args.matrix:
        for wav in wavs:
            for q in default_questions:
                _run_one(wav, q)
        return

    pairs: list[tuple[Path, str]] = []
    for i, w in enumerate(wavs):
        pairs.append((w, default_questions[i % len(default_questions)]))
    for wav, question in pairs:
        _run_one(wav, question)


if __name__ == "__main__":
    main()
