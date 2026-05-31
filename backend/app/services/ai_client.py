"""并发调用 ASR、声纹、情感子服务。"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _asr_ok(body: dict[str, Any]) -> tuple[bool, str]:
    status = (body.get("status") or "").lower()
    if status == "success" and body.get("answer_correct") is True:
        return True, body.get("recognized_text") or ""
    msg = body.get("message") or status or "ASR 未通过"
    return False, str(msg)


async def call_asr(
    client: httpx.AsyncClient,
    audio: bytes,
    filename: str,
    question: str,
) -> dict[str, Any]:
    url = settings.asr_verify_url.strip()
    if not url:
        return {"ok": False, "error": "未配置 ASR_VERIFY_URL", "raw": {}}
    try:
        files = {"audio": (filename or "answer.wav", audio, "application/octet-stream")}
        data = {"question": question}
        r = await client.post(url, files=files, data=data, timeout=settings.ai_http_timeout_sec)
        r.raise_for_status()
        body = r.json()
    except Exception as e:  # noqa: BLE001
        logger.exception("ASR 调用失败: %s", e)
        return {"ok": False, "error": str(e), "raw": {}}
    ok, text = _asr_ok(body)
    return {"ok": ok, "recognized_text": text, "error": "" if ok else "口令或语音识别未通过", "raw": body}


async def call_voiceprint(
    client: httpx.AsyncClient,
    user_id: int,
    audio: bytes,
    filename: str,
) -> dict[str, Any]:
    if settings.mock_voiceprint_match:
        return {"ok": True, "error": "", "raw": {"mock": True}}

    url = settings.voice_verify_url.strip()
    if not url:
        if settings.voice_verify_allow_segments_stub:
            base = settings.data_dir / "voiceprints" / str(user_id)
            needed = [base / f"seg{i}.wav" for i in (1, 2, 3)]
            if all(p.is_file() for p in needed):
                return {"ok": True, "error": "", "raw": {"stub": "local_segments"}}
            return {
                "ok": False,
                "error": "尚未完成声纹录入（缺少分段 wav）",
                "raw": {"stub": "missing_files"},
            }
        return {
            "ok": False,
            "error": (
                "未配置声纹核验地址：请在 backend .env 设置 VOICE_VERIFY_URL="
                "http://127.0.0.1:8002/api/v1/voice/verify，并启动 ai-vpr-ser；"
                "在其 .env 设置 VOICEPRINTS_ROOT 指向本后端 DATA_DIR/voiceprints。"
                "（仅本地假通过可设 VOICE_VERIFY_ALLOW_SEGMENTS_STUB=true）"
            ),
            "raw": {"stub": "no_verify_url"},
        }

    try:
        files = {"audio": (filename or "answer.wav", audio, "application/octet-stream")}
        data = {"user_id": str(user_id)}
        r = await client.post(url, files=files, data=data, timeout=settings.ai_http_timeout_sec)
        r.raise_for_status()
        body = r.json()
    except Exception as e:  # noqa: BLE001
        logger.exception("声纹服务调用失败: %s", e)
        return {"ok": False, "error": str(e), "raw": {}}

    ok = bool(body.get("match") or body.get("ok") or body.get("success"))
    return {"ok": ok, "error": "" if ok else "声纹不匹配", "raw": body}


# ──────────────────────────────────────────────
# 声纹注册：将三段 WAV 发给 ai-vpr-ser 生成特征向量
# ──────────────────────────────────────────────
async def call_voice_enroll(
    user_id: int,
    segments: list[tuple[bytes, str]],
) -> dict[str, Any]:
    """
    调用声纹服务的 /api/v1/voice/enroll 接口注册声纹。

    参数
    ----
    user_id  : 用户 ID
    segments : [(wav_bytes, filename), ...] 三段录音
    """
    url = settings.voice_enroll_url.strip()
    if not url:
        logger.warning("未配置 VOICE_ENROLL_URL，跳过声纹特征注册（仅保存原始 WAV）")
        return {"ok": True, "error": "", "raw": {"skipped": True, "reason": "no_enroll_url"}}

    try:
        files = {
            f"segment{i+1}": (
                name or f"seg{i+1}.wav",
                blob,
                "application/octet-stream",
            )
            for i, (blob, name) in enumerate(segments)
        }
        data = {"user_id": str(user_id)}
        async with httpx.AsyncClient(timeout=settings.ai_http_timeout_sec) as client:
            r = await client.post(url, files=files, data=data)
            r.raise_for_status()
            body = r.json()
    except Exception as e:  # noqa: BLE001
        logger.exception("声纹注册调用失败: %s", e)
        return {"ok": False, "error": str(e), "raw": {}}

    enroll_ok = bool(body.get("success") or body.get("ok"))
    return {
        "ok": enroll_ok,
        "error": "" if enroll_ok else body.get("message", "声纹注册失败"),
        "raw": body,
    }


def _parse_duress(body: dict[str, Any]) -> tuple[bool, str]:
    if body.get("duress") or body.get("coercion"):
        return True, "coercion"
    em = (body.get("emotion") or body.get("label") or "").lower()
    if em in ("coercion", "fear", "duress", "胁迫", "恐惧"):
        return True, em or "coercion"
    return False, em or "neutral"


async def call_emotion(
    client: httpx.AsyncClient,
    user_id: int,
    audio: bytes,
    filename: str,
) -> dict[str, Any]:
    if settings.mock_emotion_duress:
        return {"duress": True, "emotion": "coercion", "error": "", "raw": {"mock": True}}

    url = settings.emotion_analyze_url.strip()
    if not url:
        return {"duress": False, "emotion": "neutral", "error": "", "raw": {"stub": True}}

    try:
        files = {"audio": (filename or "answer.wav", audio, "application/octet-stream")}
        data = {"user_id": str(user_id)}
        r = await client.post(url, files=files, data=data, timeout=settings.ai_http_timeout_sec)
        r.raise_for_status()
        body = r.json()
    except Exception as e:  # noqa: BLE001
        logger.exception("情感服务调用失败: %s", e)
        return {"duress": False, "emotion": "unknown", "error": str(e), "raw": {}}

    duress, emotion = _parse_duress(body)
    return {"duress": duress, "emotion": emotion, "error": "", "raw": body}


def save_voiceprint_segments(user_id: int, segments: list[tuple[bytes, str]]) -> str:
    """保存多段 wav，返回 feature_path（JSON 路径列表）。"""
    root = settings.data_dir / "voiceprints" / str(user_id)
    root.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for i, (blob, _name) in enumerate(segments, start=1):
        p = root / f"seg{i}.wav"
        p.write_bytes(blob)
        paths.append(str(p.relative_to(settings.data_dir)))
    return json.dumps(paths, ensure_ascii=False)
