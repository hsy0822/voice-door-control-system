"""SpeechBrain：ECAPA 声纹嵌入 + wav2vec2 情感（IEMOCAP）。"""

from __future__ import annotations

import logging
import os

# 首次运行会从 Hugging Face 拉取权重；直连 huggingface.co 在国内常超时，hub 会多次重试导致很慢。
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
# HF 缓存在 Windows 上默认用 symlink；无开发者模式时设为 1 可避免告警并改用复制缓存
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
# Py3.13 + 新版 torch：先导入 transformers 再导入 speechbrain，否则 torch 注册算子时 inspect 会触发 SB LazyModule，导致情感备用导入失败
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
# 未指定 HF_ENDPOINT 时默认走国内常用镜像（与 huggingface_hub 约定一致）。必须用官方站时请在 .env 设置：
#   HF_USE_OFFICIAL_HUB=1
# 或显式：HF_ENDPOINT=https://huggingface.co
if not (os.environ.get("HF_ENDPOINT") or "").strip():
    if os.environ.get("HF_USE_OFFICIAL_HUB", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


def _install_k2_stub_if_needed() -> None:
    """SpeechBrain 1.x 在部分导入链上会执行 import k2；门禁不需要真 k2，占位可避免 ImportError。"""
    if os.environ.get("VPR_SKIP_K2_STUB", "").strip().lower() in ("1", "true", "yes"):
        return
    import sys
    import types

    if "k2" not in sys.modules:
        sys.modules["k2"] = types.ModuleType("k2")


_install_k2_stub_if_needed()

import re
import threading
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
import torchaudio


def _warm_transformers_before_speechbrain() -> None:
    """
    在首次加载 SpeechBrain 之前完成 transformers 中与情感相同的导入链。
    仅 ``import transformers`` 不会急切加载 ``modeling_auto``/``GenerationMixin``；
    若在 SB 之后再首次 ``from transformers import AutoModel*``，会在 Py3.13+torch 下触发
    ``wait_tensor`` 重复注册与 LazyModule 冲突。
    """
    log = logging.getLogger(__name__)
    try:
        import transformers  # noqa: F401

        from transformers import (  # noqa: F401
            AutoFeatureExtractor,
            AutoModelForAudioClassification,
        )
    except Exception as e:  # noqa: BLE001
        log.warning(
            "transformers 急切预热失败（情感备用可能不可用，声纹仍可用）: %s", e
        )
        return
    log.info("transformers 已急切预热（AutoModel，早于 SpeechBrain）")


_warm_transformers_before_speechbrain()

from app import config

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_spk_model: Any = None
_emo_model: Any = None  # SpeechBrain 实例 | HFEmotionTransformersBackend | NeutralEmotionBackend


class NeutralEmotionBackend:
    """SpeechBrain / transformers 均失败时使用，避免接口 500。"""

    def classify_path(self, wav_path: Path) -> dict[str, Any]:
        return {
            "emotion": "neutral",
            "confidence": 0.0,
            "duress": False,
            "coercion": False,
            "label_raw": "neutral(no_model)",
        }


class HFEmotionTransformersBackend:
    """
    用 Hugging Face AutoModel 做情感分类，避免 pipeline() 在部分环境下仍触发 SpeechBrain/k2 解析链。
    """

    __slots__ = ("model", "extractor", "id2label", "torch_device")

    def __init__(
        self,
        model: Any,
        extractor: Any,
        id2label: dict[int, str],
        torch_device: torch.device,
    ) -> None:
        self.model = model
        self.extractor = extractor
        self.id2label = id2label
        self.torch_device = torch_device

    def classify_path(self, wav_path: Path) -> dict[str, Any]:
        sig, fs = torchaudio.load(str(wav_path.resolve()))
        if sig.shape[0] > 1:
            sig = sig.mean(dim=0, keepdim=True)
        sr = int(fs)
        if sr != config.TARGET_SR:
            sig = torchaudio.functional.resample(
                sig, orig_freq=sr, new_freq=config.TARGET_SR
            )
            sr = config.TARGET_SR
        wave = sig.squeeze().detach().cpu().numpy()
        inputs = self.extractor(wave, sampling_rate=sr, return_tensors="pt")
        inputs = {k: v.to(self.torch_device) for k, v in inputs.items()}
        with torch.no_grad():
            logits = self.model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        score, idx = torch.max(probs, dim=-1)
        idx_i = int(idx.item())
        score_f = float(score.item())
        label = self.id2label.get(idx_i) or self.id2label.get(str(idx_i)) or str(idx_i)
        lab_l = str(label).lower().strip()
        duress_sub = any(s in lab_l for s in config.DURESS_SUBSTRINGS)
        neutralish = any(
            x in lab_l
            for x in (
                "neu",
                "neutral",
                "calm",
                "hap",
                "happy",
                "joy",
                "平静",
                "中性",
            )
        )
        duress_prob = (not neutralish) and score_f >= config.DURESS_MIN_PROB
        duress = bool(duress_sub or duress_prob)
        return {
            "emotion": str(label),
            "confidence": round(score_f, 4),
            "duress": duress,
            "coercion": duress,
            "label_raw": str(label),
        }


def _device() -> str:
    d = (config.DEVICE or "cpu").strip().lower()
    if d.startswith("cuda") and torch.cuda.is_available():
        return d
    return "cpu"


def _sb_local_strategy():
    """Windows 默认无符号链接权限时 SYMLINK 会 WinError 1314，改用复制。"""
    from speechbrain.utils.fetching import LocalStrategy

    raw = (os.environ.get("SB_FETCH_LOCAL_STRATEGY") or "").strip().upper()
    if raw == "SYMLINK":
        return LocalStrategy.SYMLINK
    if raw in ("COPY", ""):
        return LocalStrategy.COPY
    if raw == "COPY_SKIP_CACHE":
        return LocalStrategy.COPY_SKIP_CACHE
    return LocalStrategy.COPY


def get_spk_model() -> Any:
    global _spk_model
    with _lock:
        if _spk_model is None:
            from speechbrain.inference.classifiers import EncoderClassifier

            savedir = config.MODELS_DIR / "spkrec-ecapa-voxceleb"
            savedir.mkdir(parents=True, exist_ok=True)
            ls = _sb_local_strategy()
            logger.info("加载声纹模型 %s -> %s (local_strategy=%s)", config.SPKREC_SOURCE, savedir, ls.name)
            _spk_model = EncoderClassifier.from_hparams(
                source=config.SPKREC_SOURCE,
                savedir=str(savedir),
                run_opts={"device": _device()},
                local_strategy=ls,
            )
    return _spk_model


def _load_hf_emotion_automodel() -> HFEmotionTransformersBackend:
    """仅用 transformers 的 Auto* API，不经过 pipeline，减少与 SpeechBrain 的交叉导入。"""
    _install_k2_stub_if_needed()
    from transformers import AutoModelForAudioClassification, AutoFeatureExtractor

    mid = config.EMOTION_HF_MODEL
    logger.info("加载情感备用模型 (transformers AutoModel): %s", mid)
    extractor = AutoFeatureExtractor.from_pretrained(mid)
    model = AutoModelForAudioClassification.from_pretrained(mid)
    torch_dev = torch.device(_device())
    model = model.to(torch_dev)
    model.eval()
    raw = getattr(model.config, "id2label", None) or {}
    id2label: dict[int, str] = {}
    for k, v in raw.items():
        try:
            id2label[int(k)] = str(v)
        except (TypeError, ValueError):
            pass
    return HFEmotionTransformersBackend(model, extractor, id2label, torch_dev)


def _load_emotion_backend() -> Any:
    """优先 SpeechBrain IEMOCAP；失败时（常见：缺少 k2）改用 transformers。"""
    savedir = config.MODELS_DIR / "emotion-wav2vec2-iemocap"
    savedir.mkdir(parents=True, exist_ok=True)
    logger.info("尝试 SpeechBrain 情感模型 %s -> %s", config.EMOTION_SOURCE, savedir)
    ls = _sb_local_strategy()
    try:
        from speechbrain.inference.interfaces import foreign_class

        return foreign_class(
            source=config.EMOTION_SOURCE,
            pymodule_file="custom_interface.py",
            classname="CustomEncoderWav2vec2Classifier",
            savedir=str(savedir),
            run_opts={"device": _device()},
            local_strategy=ls,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("SpeechBrain foreign_class 情感加载失败: %s", e)
    try:
        from speechbrain.inference.classifiers import EncoderClassifier

        return EncoderClassifier.from_hparams(
            source=config.EMOTION_SOURCE,
            savedir=str(savedir),
            run_opts={"device": _device()},
            local_strategy=ls,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("SpeechBrain EncoderClassifier 情感加载失败: %s", e)
    try:
        return _load_hf_emotion_automodel()
    except Exception as e:  # noqa: BLE001
        logger.warning("transformers 情感备用加载失败: %s", e, exc_info=True)
    logger.warning("情感模型不可用，将返回 neutral 占位（胁迫检测不会触发）")
    return NeutralEmotionBackend()


def get_emo_model() -> Any:
    global _emo_model
    with _lock:
        if _emo_model is None:
            _emo_model = _load_emotion_backend()
    return _emo_model


def _wav_tensor_from_path(wav_path: Path) -> torch.Tensor:
    import soundfile as sf
    sig, fs = sf.read(str(wav_path.resolve()))
    if sig.ndim > 1:
        sig = sig.mean(axis=1)
    if int(fs) != config.TARGET_SR:
        import librosa
        sig = librosa.resample(sig, orig_sr=int(fs), target_sr=config.TARGET_SR)
    return torch.from_numpy(sig).unsqueeze(0).float()
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
    if not config.VOICEPRINTS_ROOT:
        return None

    # 强制进入用户子文件夹：voiceprints/2/
    root = Path(config.VOICEPRINTS_ROOT) / str(user_id)
    paths = [root / f"seg{i}.wav" for i in (1, 2, 3)]

    # 强制检查文件是否存在
    if not all(p.is_file() for p in paths):
        return None

    # 强制生成声纹模型
    embs = [embedding_from_wav_path(p) for p in paths]
    cen = np.mean(np.stack(embs, axis=0), axis=0).astype(np.float32)
    cen = cen / (float(np.linalg.norm(cen)) + 1e-8)

    outp = enrollment_path(user_id)
    print(f"Creating enrollment at: {outp}")
    outp.parent.mkdir(parents=True, exist_ok=True)
    np.save(outp, cen)
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
    if isinstance(emo, (HFEmotionTransformersBackend, NeutralEmotionBackend)):
        return emo.classify_path(wav_path)
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


def preload_models() -> tuple[bool, bool]:
    """返回 (声纹是否就绪, 情感是否为真实模型而非 neutral 占位)。"""
    spk_ok = True
    try:
        get_spk_model()
    except Exception as e:  # noqa: BLE001
        spk_ok = False
        logger.exception("声纹模型预加载失败: %s", e)
    get_emo_model()
    emo_real = emotion_model_ready()
    return spk_ok, emo_real


def speaker_model_ready() -> bool:
    return _spk_model is not None


def emotion_model_ready() -> bool:
    if _emo_model is None:
        return False
    return not isinstance(_emo_model, NeutralEmotionBackend)
