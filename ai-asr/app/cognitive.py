"""动态认知口令解析与用户回答校验（算术 / 常识，支持模糊匹配）。"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Tuple

# 中文数字 -> 阿拉伯数字（门禁短答）
_CN_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace(" ", "").replace("\u3000", "")
    return s.strip()


def _normalize_question(s: str) -> str:
    s = _normalize_text(s)
    s = s.replace("？", "?").replace("＝", "=").replace("－", "-").replace("—", "-")
    s = s.replace("＋", "+")
    return s


def _normalize_arithmetic_asr_typos(t: str) -> str:
    """口算短答里 ASR 常见误字（八 被写成 吧）。"""
    t = t.replace("答案是吧", "答案是八")
    t = t.replace("等于吧", "等于八")
    return t


def _strip_leading_fillers(t: str) -> str:
    """去掉句首语气字 / 误识别的「把」等。"""
    while t and t[0] in "把呃嗯啊哦噢诶呀哎哼啧":
        t = t[1:]
    return t


def _extract_int_arithmetic_fallback(t: str) -> Optional[int]:
    """
    算术短答兜底：ASR 常把「答案是三」听成「暗示三」「把暗示三」等，
    在无法按严格句式解析时，从短句里抽取最可能的个位数答案。
    """
    t = _normalize_arithmetic_asr_typos(_normalize_text(t))
    t = re.sub(r"[。，、！？·]", "", t)
    t = _strip_leading_fillers(t.replace(" ", "").replace("\u3000", ""))
    if not t:
        return None

    # 「暗示」常与「答案是」音近，后跟个位数
    m_hint = re.search(r"暗示([一二三四五六七八九十零〇两])", t)
    if m_hint:
        ch = m_hint.group(1)
        if ch in _CN_DIGITS:
            return int(_CN_DIGITS[ch])

    # 句末单个中文数字（「答案是三」「一加二是三」等）；含「十」的合成数交给上文规则，避免「三十六」误判成 6
    if len(t) <= 16 and "十" not in t:
        for ch in reversed(t):
            if ch in _CN_DIGITS and ch != "十":
                return int(_CN_DIGITS[ch])

    # 句末阿拉伯数字
    m_tail = re.search(r"(\d)\s*$", t)
    if m_tail:
        return int(m_tail.group(1))

    return None


def _extract_int_from_answer(text: str) -> Optional[int]:
    """从识别文本中提取整数答案（阿拉伯或中文）。"""
    t = _normalize_arithmetic_asr_typos(_normalize_text(text))
    m = re.search(r"-?\d+", t)
    if m:
        try:
            return int(m.group(0))
        except ValueError:
            pass
    # 简单中文数字：十 / 十几 / 几十几
    if not t:
        return None
    if t in ("十",):
        return 10
    m2 = re.match(r"^十([一二三四五六七八九])$", t)
    if m2:
        return 10 + _CN_DIGITS.get(m2.group(1), 0)
    m3 = re.match(r"^([一二三四五六七八九])十([一二三四五六七八九]?)$", t)
    if m3:
        tens = _CN_DIGITS.get(m3.group(1), 0) * 10
        ones = _CN_DIGITS.get(m3.group(2), 0) if m3.group(2) else 0
        return tens + ones
    if len(t) == 1 and t in _CN_DIGITS:
        return int(_CN_DIGITS[t])
    # 「答案是八」「答案8」等句式（允许「答案」与「是」之间略有噪声）
    m_ans = re.search(
        r"答案[^是为]{0,3}(?:是|为|：|:)?\s*([一二三四五六七八九十两零〇0-9])",
        t,
    )
    if not m_ans:
        m_ans = re.search(r"答案(?:是|为|：|:)?\s*([一二三四五六七八九十两零〇0-9])", t)
    if m_ans:
        ch = m_ans.group(1)
        if ch in _CN_DIGITS:
            return int(_CN_DIGITS[ch])
        if ch.isdigit():
            return int(ch)

    return _extract_int_arithmetic_fallback(t)


def _parse_arithmetic(question: str) -> Optional[Tuple[str, int, int]]:
    """
    解析加法或减法题，返回 (op, a, b)；无法解析则 None。
    op 为 '+' 或 '-'
    """
    q = _normalize_question(question)
    # 3+5=?  7-2?
    m_add = re.match(r"^(\d+)\s*\+\s*(\d+)\s*\=?\s*\??$", q)
    if m_add:
        return "+", int(m_add.group(1)), int(m_add.group(2))
    m_sub = re.match(r"^(\d+)\s*-\s*(\d+)\s*\=?\s*\??$", q)
    if m_sub:
        return "-", int(m_sub.group(1)), int(m_sub.group(2))
    return None


def _expected_number_for_arithmetic(question: str) -> Optional[int]:
    parsed = _parse_arithmetic(question)
    if not parsed:
        return None
    op, a, b = parsed
    if op == "+":
        return a + b
    return a - b


# 常识题：(题目关键词列表, 可接受答案片段列表)
_TRIVIA_RULES: List[Tuple[List[str], List[str]]] = [
    (["天空", "天是什么颜色", "天的颜色"], ["蓝色", "蓝", "天蓝", "蔚蓝"]),
    (["草", "草地", "草是什么颜色"], ["绿色", "绿", "草绿", "翠绿"]),
    (["树叶", "叶子", "叶子什么颜色"], ["绿色", "绿"]),
    (["雪", "雪是什么颜色"], ["白色", "白"]),
    (["太阳", "太阳什么颜色", "阳光"], ["黄色", "黄", "金色", "金"]),
]


def _match_trivia(question: str) -> Optional[List[str]]:
    qn = _normalize_question(question)
    for keys, accepts in _TRIVIA_RULES:
        if any(k in qn for k in keys):
            return accepts
    return None


def is_arithmetic_question(question: str) -> bool:
    """是否为已支持的加减口算题（供 ASR 侧策略使用）。"""
    return _parse_arithmetic(question) is not None


def whisper_context_prompt(question: str) -> str:
    """
    供 Whisper initial_prompt 使用的中文语境（不含题目答案）。

    注意：initial_prompt 里不要枚举「一二三四…」或颜色列表，短音频时 Whisper
    容易把提示词当作正文反复复读，造成幻觉转写。
    """
    q = (question or "").strip()
    if not q:
        return "门禁短答。"
    if _parse_arithmetic(q) is not None:
        return "门禁口算，用户只报一个得数。"
    if _match_trivia(_normalize_question(q)):
        return "门禁常识，用户只报颜色。"
    return "门禁短答。"


def _fuzzy_accept(user: str, accepted_fragments: List[str]) -> bool:
    u = _normalize_text(user)
    if not u:
        return False
    for frag in accepted_fragments:
        f = _normalize_text(frag)
        if not f:
            continue
        if f in u or u in f:
            return True
    return False


@dataclass
class ValidationResult:
    correct: bool
    question_type: str  # arithmetic | trivia | unknown
    expected_display: str
    reason: str


def validate_answer(question: str, recognized_text: str) -> ValidationResult:
    """
    根据题目与用户识别文本给出是否回答正确。
    recognized_text 为空视为错误。
    """
    q = (question or "").strip()
    text = (recognized_text or "").strip()

    if not q:
        return ValidationResult(
            correct=False,
            question_type="unknown",
            expected_display="",
            reason="题目为空",
        )

    exp_num = _expected_number_for_arithmetic(q)
    if exp_num is not None:
        got = _extract_int_from_answer(text)
        ok = got is not None and got == exp_num
        return ValidationResult(
            correct=ok,
            question_type="arithmetic",
            expected_display=str(exp_num),
            reason="算术答案匹配" if ok else f"期望数字 {exp_num}，识别为 {got!r}",
        )

    accepts = _match_trivia(q)
    if accepts:
        ok = _fuzzy_accept(text, accepts)
        disp = " / ".join(accepts[:3])
        return ValidationResult(
            correct=ok,
            question_type="trivia",
            expected_display=disp,
            reason="常识模糊匹配通过" if ok else "未匹配到可接受答案",
        )

    # 未知题型：保守判定为不通过（避免漏判录音攻击）
    return ValidationResult(
        correct=False,
        question_type="unknown",
        expected_display="",
        reason="未识别的题目类型，请在 cognitive 模块补充规则",
    )
