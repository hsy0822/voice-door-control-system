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

### 删除子目录里旧的 `.venv`

若提示「拒绝访问」或 `.pyd` 被占用：先**关掉**所有用该 venv 的终端、Python 调试进程和 IDE 里选中的该解释器，再删除 `backend\.venv`、`ai-vpr-ser\.venv` 等；仍删不掉可注销/重启后再删。
