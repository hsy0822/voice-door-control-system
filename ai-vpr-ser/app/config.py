"""ai-vpr-ser 服务配置（环境变量覆盖）。"""

from __future__ import annotations

import os
from pathlib import Path

# 项目根：ai-vpr-ser/
try:
    BASE_DIR = Path(__file__).resolve().parent.parent
except (NameError, TypeError):
    # For -c or other cases where __file__ is not available
    import sys
    if hasattr(sys, '_getframe'):
        frame = sys._getframe(1)
        caller_file = frame.f_code.co_filename
        if caller_file and caller_file != '<string>':
            BASE_DIR = Path(caller_file).resolve().parent.parent
        else:
            BASE_DIR = Path.cwd()
    else:
        BASE_DIR = Path.cwd()

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

HOST = os.environ.get("VPR_SER_HOST", "0.0.0.0")
PORT = int(os.environ.get("VPR_SER_PORT", "8002"))

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = Path(os.environ.get("VPR_SER_MODELS_DIR", str(BASE_DIR / "pretrained_models")))
TEMP_DIR = Path(os.environ.get("VPR_SER_TEMP_DIR", str(BASE_DIR / "temp")))
LOG_DIR = Path(os.environ.get("VPR_SER_LOG_DIR", str(BASE_DIR / "logs")))

# 与后端 data/voiceprints 对齐：若已存在 seg1–3.wav，可在首次 verify 时自动建库
VOICEPRINTS_ROOT = Path(os.environ.get("VOICEPRINTS_ROOT", "")) if os.environ.get(
    "VOICEPRINTS_ROOT", ""
).strip() else None

TARGET_SR = 16000
# 与门禁短答对齐；过短易 400（trim 后常见 0.35–0.5s）
MIN_DURATION_SEC = float(os.environ.get("VPR_MIN_DURATION_SEC", "0.35"))
MAX_DURATION_SEC = float(os.environ.get("VPR_MAX_DURATION_SEC", "5.0"))
MAX_UPLOAD_BYTES = int(os.environ.get("VPR_MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))

# SpeechBrain Hub 模型 ID（首次运行会下载到 MODELS_DIR 下对应子目录）
SPKREC_SOURCE = os.environ.get("SPKREC_SOURCE", "speechbrain/spkrec-ecapa-voxceleb")
EMOTION_SOURCE = os.environ.get("EMOTION_SOURCE", "speechbrain/emotion-recognition-wav2vec2-IEMOCAP")
# SpeechBrain 情感失败时（如缺少 k2）改用 Hugging Face transformers 音频分类
EMOTION_HF_MODEL = os.environ.get(
    "EMOTION_HF_MODEL",
    "superb/wav2vec2-base-superb-er",
)

DEVICE = os.environ.get("VPR_SER_DEVICE", "cpu")

# 余弦相似度阈值（越高越严），典型同一人 0.45–0.85
VOICE_MATCH_THRESHOLD = float(os.environ.get("VOICE_MATCH_THRESHOLD", "0.32"))

# 情感标签中含以下子串则视为胁迫相关（IEMOCAP 英文标签为主）
DURESS_SUBSTRINGS = tuple(
    x.strip().lower()
    for x in os.environ.get(
        "DURESS_SUBSTRINGS",
        "ang,sad,fear,fea,fru,disg,anx,scared,anger,frustrat",
    ).split(",")
    if x.strip()
)

# 非中性且置信度超过该值时，辅助提高灵敏度（与标签子串二选一满足即可标胁迫）
DURESS_MIN_PROB = float(os.environ.get("DURESS_MIN_PROB", "0.55"))
