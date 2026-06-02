"""在 ai-vpr-ser 目录下：python run_server.py

必须在 import app 之前加载 .env，否则 HF_ENDPOINT 等不会生效。
"""

import os
import sys
import types

os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

# 与 app.engine 一致：避免 SpeechBrain 可选 k2 在部分导入顺序下报错
if "k2" not in sys.modules:
    sys.modules["k2"] = types.ModuleType("k2")

from pathlib import Path

try:
    from dotenv import load_dotenv

    _root = Path(__file__).resolve().parent
    load_dotenv(_root / ".env")
except ImportError:
    pass

import uvicorn

from app.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        workers=1,
    )
