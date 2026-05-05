# 华为云 ECS 部署说明（AI-ASR）

## 1. 系统准备

- 推荐镜像：Ubuntu 22.04 LTS
- 安装 Python 3.9+、`python3-venv`，以及音频解码依赖（按需）：

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg libsndfile1
```

## 2. 部署代码

将仓库 `ai-asr` 目录同步至服务器，例如 `/opt/voice-door/ai-asr`。

## 3. 虚拟环境与依赖

```bash
cd /opt/voice-door/ai-asr
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 4. systemd 示例

`/etc/systemd/system/ai-asr.service`：

```ini
[Unit]
Description=Voice Door AI-ASR
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/voice-door/ai-asr
Environment=ASR_HOST=0.0.0.0
Environment=ASR_PORT=8090
Environment=WHISPER_MODEL=base
ExecStart=/opt/voice-door/ai-asr/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-asr
sudo systemctl status ai-asr
```

## 5. 安全组与反向代理

- 控制台安全组放行 **8090**（或实际端口）。
- 若仅内网后端调用，可不暴露公网，由 VPC 内访问 `http://<内网IP>:8090`。

## 6. 模型离线

在可联网机器下载模型后，将 `~/.cache/whisper` 目录打包复制到 ECS 同路径用户家目录下，可实现安装后**完全离线**推理。
