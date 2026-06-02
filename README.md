# voice-door-control-system
动态声纹智能门禁系统

## Python 环境（单一 venv）

后端、AI-ASR、ai-vpr-ser 共用**仓库根目录**一份依赖，避免多套 `torch` / `librosa`。

```powershell
cd <本仓库根目录>
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\pip install -r requirements.txt
```

启动时进入子目录，仍用根目录解释器，例如：

```powershell
cd backend
..\.venv\Scripts\python run_server.py
```

```powershell
cd ai-asr
..\.venv\Scripts\python run_server.py
```

```powershell
cd ai-vpr-ser
..\.venv\Scripts\python run_server.py
```

可选 FunASR：在装好根 `requirements.txt` 后执行 `pip install -r ai-asr/requirements-funasr.txt`。

## 一键启动（Windows）

在已创建根目录 `.venv` 并 `pip install -r requirements.txt` 之后：

- **双击** 仓库根目录的 `start-dev.bat`，或 PowerShell 执行：
  - `.\scripts\start-dev.ps1`
- 会依次打开多个新窗口：**后端 :8000**、**ASR :8090**、**ai-vpr-ser :8002**、**前端 :5173**（首次前端会自动 `npm install`）。
- 仅 Python、不要前端：`.\scripts\start-dev.ps1 -NoFrontend`
- 不要声纹服务：`.\scripts\start-dev.ps1 -NoVprSer`
- 尝试关掉默认端口上的进程：`.\scripts\stop-dev.ps1`（需 PowerShell 能使用 `Get-NetTCPConnection`）

### ai-vpr-ser 首次启动很慢 / Hugging Face 超时

这是 **SpeechBrain 从 Hugging Face 下载预训练权重**（如 `spkrec-ecapa-voxceleb`）的步骤；直连 `huggingface.co` 失败时 **hub 会多次重试**，日志里会出现 `Retrying...`。

**默认行为**：未设置 `HF_ENDPOINT` 时，代码会改用 **`https://hf-mirror.com`**（见 `ai-vpr-ser/app/engine.py`）。请用 **`python run_server.py`** 启动（已在 `run_server.py` 里最先加载 `.env`）；若仍走官方域名，多半是旧进程或未重启。

**可选**：在 **`ai-vpr-ser/.env`** 里显式写 `HF_ENDPOINT=...`；必须用官方站时设 **`HF_USE_OFFICIAL_HUB=1`**。离线可把模型拷到 **`pretrained_models/`** 后设 **`HF_HUB_OFFLINE=1`**。详见 `ai-vpr-ser/env.example`。

### 删除子目录里旧的 `.venv`

若提示「拒绝访问」或 `.pyd` 被占用：先**关掉**所有用该 venv 的终端、Python 调试进程和 IDE 里选中的该解释器，再删除 `backend\.venv`、`ai-vpr-ser\.venv` 等；仍删不掉可注销/重启后再删。
