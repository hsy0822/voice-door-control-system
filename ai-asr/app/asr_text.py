"""ASR 输出共用清洗与算术题下单字过滤。"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from app.cognitive import is_arithmetic_question
from app.config import DROP_ARITHMETIC_SINGLE_GARBAGE

_FILLER_RE = re.compile(r"[嗯呃啊哦欸诶呀哈哼]+")

# 算术题下常见单字误识别（模型幻觉/语气），不当作有效答案
_ARITHMETIC_GARBAGE_SINGLE = frozenset(
    {"好", "嗯", "哦", "噢", "唉", "诶", "哈", "哼", "呀", "哎", "对", "行", "是"}
)


def clean_chinese_text(text: str) -> str:
    t = (text or "").strip()
    t = _FILLER_RE.sub("", t)
    t = re.sub(r"\s+", "", t)
    return t.strip()


def filter_arithmetic_single_garbage(
    cleaned: str, question: Optional[str]
) -> Tuple[str, bool]:
    """算术题且单字为语气词时丢弃。返回 (文本, 是否发生过过滤)。"""
    if not DROP_ARITHMETIC_SINGLE_GARBAGE:
        return cleaned, False
    if (
        question
        and is_arithmetic_question(question)
        and len(cleaned) == 1
        and cleaned in _ARITHMETIC_GARBAGE_SINGLE
    ):
        return "", True
    return cleaned, False
