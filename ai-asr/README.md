# AI-ASR 模块（何淑煜）

纯本地部署：音频标准化 → **ASR（默认 Whisper；可选 FunASR 中文 Paraformer）** → 动态认知问答校验。不调用在线语音识别 API，可部署于华为云 ECS。

## 功能概览

| 能力 | 说明 |
|------|------|
| 预处理 | 转 16kHz / 单声道 / WAV PCM16、谱减法降噪、首尾静音裁剪、有效时长默认 **0.5–5s** 校验、峰值归一化 |
| ASR | 默认 **OpenAI Whisper**；装 [`requirements-funasr.txt`](requirements-funasr.txt) 并设 `ASR_ENGINE=funasr` 后使用 **[FunASR](https://github.com/modelscope/FunASR) `paraformer-zh`**（短中文、数字在多数场景**往往**比同体量 Whisper 更稳，非 100% 保证） |
| 认知校验 | 算术（加减）、常识题模糊匹配；未知题型保守判错 |
| HTTP 服务 | FastAPI，`/health`、`/api/v1/verify`，CORS 全开便于联调 |
| 日志 | `logs/asr.log` 滚动文件 + 控制台 |

## 环境要求

- Python **3.9+**（文档验收写 3.9；开发与 CI 可用 3.10–3.13）
- 独立虚拟环境（勿与 backend、ai-vpr-ser 混用）
- 首次运行会从网络**下载 ASR 权重**（FunASR 走 ModelScope 等；Whisper 走官方缓存）；缓存完成后可断网推理

## 安装与启动

```bash
cd ai-asr
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

（可选）启用 **FunASR 路线 C**（建议在 **Linux / 华为云 ECS** 上安装；Windows 若依赖编译失败可用 WSL 或继续用 Whisper）：

```bash
python -m pip install -r requirements-funasr.txt
export ASR_ENGINE=funasr
```

**Windows 安装 `requirements-funasr.txt` 若卡在 `editdistance` / `math.h`：** 说明正在本地编译 C 扩展但缺少 Windows SDK。可按 [`requirements-funasr.txt`](requirements-funasr.txt) 顶部注释处理：安装 [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)（勾选「使用 C++ 的桌面开发」与 **Windows 11 SDK**）、或改用 **Python 3.11/3.12** 新建 venv、或使用 **WSL2**。装不上时保持 **`ASR_ENGINE=whisper`** 即可，服务会自动走 Whisper。

**本机已用 Miniconda 装好 Python 3.11（64 位）+ 全量依赖时**（环境名 `voice-asr-py311`），在 PowerShell 中：

```powershell
conda activate voice-asr-py311
cd C:\Users\hesy\voice-door-control-system\ai-asr
$env:ASR_ENGINE = "funasr"
python run_server.py
```

解释器路径：`D:\IDE\miniconda3\envs\voice-asr-py311\python.exe`（在 Cursor 里选「解释器」时也可直接选这个）。**项目里原来的 `.venv` 仍是 Python 3.13**，与 Conda 环境二选一即可，勿混用。

启动服务（默认 `0.0.0.0:8090`）：

```bash
python run_server.py
```

或使用 uvicorn：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8090
```

环境变量见 `env.example`：`ASR_ENGINE`（`funasr`|`whisper`）、`FUNASR_MODEL`、`ASR_DEVICE`（`cpu`/`cuda:0`）、`ASR_PORT`、`WHISPER_MODEL`、`ASR_MAX_CONCURRENT`。若 FunASR 加载失败，服务会**自动回退 Whisper** 并打日志。

## 接口说明（供后端 黄鸿煜 联调）

### `GET /health`

健康检查，返回当前配置的模型名。

### `POST /api/v1/verify`

- **Content-Type**: `multipart/form-data`
- **字段**:
  - `audio`: 二进制文件（wav / mp3 / webm 等常见格式）
  - `question`: 文本，后端下发的认知题目（如 `3+5=?`、`天空是什么颜色？`）

**成功示例 JSON**（业务错误也用 HTTP 200，见 `status` 字段）：

```json
{
  "status": "success",
  "recognized_text": "8",
  "answer_correct": true,
  "question_type": "arithmetic",
  "expected_answer": "8",
  "message": "算术答案匹配",
  "audio_meta": { "duration_sec": 1.2, "sample_rate": 16000, "channels": 1, "format": "WAV", "subtype": "PCM_16" },
  "detail_log": []
}
```

常见 `status`：`AUDIO_TOO_SHORT`、`AUDIO_TOO_LONG`、`NO_SPEECH`、`AUDIO_LOAD_FAILED`、`INTERNAL_ERROR` 等。

### curl 示例

```bash
curl -s -X POST "http://127.0.0.1:8090/api/v1/verify" \
  -F "audio=@your.wav" \
  -F "question=3+5=?"
```

## 与前端（洪欣欣）约定

- 推荐上传 **16kHz / 单声道 / WAV**；有效语音默认 **≥0.5s、≤5s**（可用环境变量 `ASR_MIN_DURATION_SEC` 调整最短时长）。
- 过短或过长会返回 `AUDIO_TOO_SHORT` / `AUDIO_TOO_LONG`。

## 与 AI-VPR/SER（黄嘉怡）对齐

- 标准化输出：**WAV、16000 Hz、mono、PCM 16 bit**；临时文件在 `ai-asr/temp/`，文件名带 UUID 前缀，避免与声纹/情感模块冲突。
- 若需共用目录，可由环境变量扩展（后续可在 `app/config.py` 增加 `TEMP_DIR` 覆盖项）。

## 华为云 ECS 部署要点

1. 使用 **systemd** 或 **supervisor** 常驻 `uvicorn`，`WorkingDirectory` 指向 `ai-asr`。
2. 安全组放行 `ASR_PORT`（默认 8090），仅对后端内网 IP 开放更佳。
3. 模型首次下载需外网；内网机可事先缓存 `~/.cache/whisper` 再拷贝至服务器。
4. **性能**：≤1s 延迟强依赖 CPU/GPU 与模型大小；CPU 上建议 `WHISPER_MODEL=tiny` 做实时门禁联调，`base`/`small` 做准确率验收（GPU 更佳）。

## 测试

```bash
cd ai-asr
python -m pytest tests/ -q
```

## 文档索引

- `docs/功能测试报告.md`：测试项与验收对照说明
