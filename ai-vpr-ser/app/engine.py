"""SpeechBrain：ECAPA 声纹嵌入 + wav2vec2 情感（IEMOCAP）。"""

from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
import torchaudio

from app import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_spk_model: Any = None
_emo_model: Any = None


def _device() -> str:
    d = (config.DEVICE or "cpu").strip().lower()
    if d.startswith("cuda") and torch.cuda.is_available():
        return d
    return "cpu"


def get_spk_model() -> Any:
    global _spk_model
    with _lock:
        if _spk_model is None:
            from speechbrain.inference.classifiers import EncoderClassifier

            savedir = config.MODELS_DIR / "spkrec-ecapa-voxceleb"
            savedir.mkdir(parents=True, exist_ok=True)
            logger.info("加载声纹模型 %s -> %s", config.SPKREC_SOURCE, savedir)
            _spk_model = EncoderClassifier.from_hparams(
                source=config.SPKREC_SOURCE,
                savedir=str(savedir),
                run_opts={"device": _device()},
            )
    return _spk_model


def get_emo_model() -> Any:
    global _emo_model
    with _lock:
        if _emo_model is None:
            savedir = config.MODELS_DIR / "emotion-wav2vec2-iemocap"
            savedir.mkdir(parents=True, exist_ok=True)
            logger.info("加载情感模型 %s -> %s", config.EMOTION_SOURCE, savedir)
            try:
                from speechbrain.inference.interfaces import foreign_class

                _emo_model = foreign_class(
                    source=config.EMOTION_SOURCE,
                    pymodule_file="custom_interface.py",
                    classname="CustomEncoderWav2vec2Classifier",
                    savedir=str(savedir),
                    run_opts={"device": _device()},
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("foreign_class 加载失败，回退 EncoderClassifier: %s", e)
                from speechbrain.inference.classifiers import EncoderClassifier

                _emo_model = EncoderClassifier.from_hparams(
                    source=config.EMOTION_SOURCE,
                    savedir=str(savedir),
                    run_opts={"device": _device()},
                )
    return _emo_model


def _wav_tensor_from_path(wav_path: Path) -> torch.Tensor:
    sig, fs = torchaudio.load(str(wav_path.resolve()))
    if sig.shape[0] > 1:
        sig = sig.mean(dim=0, keepdim=True)
    if int(fs) != config.TARGET_SR:
        sig = torchaudio.functional.resample(sig, orig_freq=int(fs), new_freq=config.TARGET_SR)
    return sig.to(_device())


def embedding_from_wav_path(wav_path: Path) -> np.ndarray:
    spk = get_spk_model()
    sig = _wav_tensor_from_path(wav_path)
    out = spk.encode_batch(sig)
    if isinstance(out, tuple):
        emb = out[0]
    else:
        emb = out
    e = emb.squeeze().detach().cpu().numpy().astype(np.float32)
    n = float(np.linalg.norm(e))
    if n > 1e-8:
        e = e / n
    return e


def enrollment_path(user_id: str) -> Path:
    safe = re.sub(r"[^\w\-]", "_", str(user_id))[:64] or "unknown"
    return config.DATA_DIR / "enrollments" / f"{safe}.npy"


def try_build_enrollment_from_voiceprints_root(user_id: str) -> Optional[Path]:
    """若配置了 VOICEPRINTS_ROOT 且存在 seg1–3.wav，则自动计算并写入注册向量。"""
    if not config.VOICEPRINTS_ROOT:
        return None
    root = config.VOICEPRINTS_ROOT / str(user_id)
    paths = [root / f"seg{i}.wav" for i in (1, 2, 3)]
    if not all(p.is_file() for p in paths):
        return None
    embs = [embedding_from_wav_path(p) for p in paths]
    cen = np.mean(np.stack(embs, axis=0), axis=0).astype(np.float32)
    cen = cen / (float(np.linalg.norm(cen)) + 1e-8)
    outp = enrollment_path(user_id)
    outp.parent.mkdir(parents=True, exist_ok=True)
    np.save(outp, cen)
    logger.info("已从 VOICEPRINTS_ROOT 自动生成声纹注册: user=%s -> %s", user_id, outp)
    return outp


def enroll_three_segments(user_id: str, wav_paths: list[Path]) -> Path:
    if len(wav_paths) != 3:
        raise ValueError("需要 3 段 wav")
    embs = [embedding_from_wav_path(p) for p in wav_paths]
    cen = np.mean(np.stack(embs, axis=0), axis=0).astype(np.float32)
    cen = cen / (float(np.linalg.norm(cen)) + 1e-8)
    outp = enrollment_path(user_id)
    outp.parent.mkdir(parents=True, exist_ok=True)
    np.save(outp, cen)
    return outp


def verify_voice(user_id: str, query_wav: Path) -> tuple[bool, float, str]:
    outp = enrollment_path(user_id)
    if not outp.is_file():
        if try_build_enrollment_from_voiceprints_root(user_id) is None:
            return False, 0.0, "未注册声纹（请先调用注册接口或配置 VOICEPRINTS_ROOT）"
    cen = np.load(outp).astype(np.float32)
    q = embedding_from_wav_path(query_wav)
    sim = float(np.dot(cen, q))
    ok = sim >= config.VOICE_MATCH_THRESHOLD
    return ok, sim, "匹配" if ok else "相似度低于阈值"


def _label_to_str(text_lab: Any) -> str:
    if text_lab is None:
        return ""
    if isinstance(text_lab, (list, tuple)) and text_lab:
        return str(text_lab[0])
    return str(text_lab)


def _max_prob(out_prob: Any) -> float:
    try:
        t = out_prob.squeeze().detach().cpu().numpy()
        return float(np.max(t))
    except Exception:  # noqa: BLE001
        return 0.0


def classify_emotion(wav_path: Path) -> dict[str, Any]:
    emo = get_emo_model()
    path_s = str(wav_path.resolve())
    if hasattr(emo, "classify_file"):
        raw = emo.classify_file(path_s)
    else:
        sig = _wav_tensor_from_path(wav_path)
        raw = emo.classify_batch(sig)

    if isinstance(raw, tuple):
        parts = list(raw)
    else:
        parts = [raw]
    out_prob = parts[0] if parts else None
    text_lab = parts[-1] if parts else ""
    label = _label_to_str(text_lab)
    lab_l = label.lower().strip().strip("[]'\"")
    conf = _max_prob(out_prob) if out_prob is not None else 0.0

    duress_sub = any(s in lab_l for s in config.DURESS_SUBSTRINGS)
    neutralish = any(
        x in lab_l for x in ("neu", "neutral", "calm", "平静", "中性")
    )
    duress_prob = (not neutralish) and conf >= config.DURESS_MIN_PROB
    duress = bool(duress_sub or duress_prob)

    return {
        "emotion": label or lab_l or "unknown",
        "confidence": round(conf, 4),
        "duress": duress,
        "coercion": duress,
        "label_raw": label,
    }


def preload_models() -> None:
    """启动时预加载，避免首次请求过慢。"""
    get_spk_model()
    try:
        get_emo_model()
    except Exception as e:  # noqa: BLE001
        logger.exception("情感模型预加载失败（情感接口将不可用）: %s", e)


def speaker_model_ready() -> bool:
    return _spk_model is not None


def emotion_model_ready() -> bool:
    return _emo_model is not None
