"""本地认知题库：算术 + 常识（与 ai-asr cognitive 规则对齐）。"""

from __future__ import annotations

import random
from typing import List, Optional

_TRIVIA = [
    "天空是什么颜色？",
    "草一般是什么颜色？",
    "雪是什么颜色？",
    "太阳看起来是什么颜色？",
    "树叶一般是什么颜色？",
]


def _random_arithmetic() -> str:
    if random.random() < 0.5:
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        return f"{a}+{b}=?"
    x = random.randint(3, 18)
    y = random.randint(1, min(9, x - 1))
    return f"{x}-{y}=?"


def pick_question(exclude: Optional[List[str]] = None) -> str:
    """随机选题，尽量避开 exclude 中的题干。"""
    exclude_set = {normalize_q(x) for x in (exclude or [])}
    for _ in range(40):
        if random.random() < 0.55:
            q = _random_arithmetic()
        else:
            q = random.choice(_TRIVIA)
        if normalize_q(q) not in exclude_set:
            return q
    return _random_arithmetic()


def normalize_q(q: str) -> str:
    return (q or "").strip().replace(" ", "").replace("\u3000", "")
