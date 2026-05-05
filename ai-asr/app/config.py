"""服务与模型配置（可通过环境变量覆盖）。"""

import os
from pathlib import Path

# 项目根：ai-asr/
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
TEMP_DIR = Path(os.environ.get("ASR_TEMP_DIR", str(BASE_DIR / "temp")))

HOST = os.environ.get("ASR_HOST", "0.0.0.0")
PORT = int(os.environ.get("ASR_PORT", "8090"))

# tiny / base / small / medium — 门禁短句建议 base 及以上；CPU 可用 tiny 做联调
WHISPER_MODEL_NAME = os.environ.get("WHISPER_MODEL", "base")

# ASR 引擎：funasr（需 pip install -r requirements-funasr.txt）| whisper（默认，免编译）
ASR_ENGINE = os.environ.get("ASR_ENGINE", "whisper").strip().lower()
# FunASR 模型名（见 FunASR 文档）；首次运行会从 ModelScope 等拉取权重
FUNASR_MODEL = os.environ.get("FUNASR_MODEL", "paraformer-zh")
# cpu / cuda:0 / cuda:1 …
ASR_DEVICE = os.environ.get("ASR_DEVICE", "cpu")

# 并发推理上限，避免多路同时加载显存/内存导致崩溃
MAX_CONCURRENT_TRANSCRIBE = int(os.environ.get("ASR_MAX_CONCURRENT", "2"))

# 上传音频最大体积（字节），默认 8MB
MAX_UPLOAD_BYTES = int(os.environ.get("ASR_MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))

TARGET_SR = 16000
# 门禁短答可短于 1s；过严易误拒。可用环境变量 ASR_MIN_DURATION_SEC 覆盖。
MIN_DURATION_SEC = float(os.environ.get("ASR_MIN_DURATION_SEC", "0.5"))
MAX_DURATION_SEC = 5.0

# 算术题下若转写仅为单个语气字（如「好」），是否丢弃；0/false/no 则保留原字
DROP_ARITHMETIC_SINGLE_GARBAGE = os.environ.get(
    "ASR_DROP_ARITHMETIC_SINGLE_GARBAGE", "1"
).strip().lower() not in ("0", "false", "no", "off", "")
