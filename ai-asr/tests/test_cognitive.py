"""认知校验单元测试（无模型依赖）。"""

import pytest

from app.cognitive import validate_answer


@pytest.mark.parametrize(
    "question,user,expect_ok",
    [
        ("3+5=?", "8", True),
        ("3+5=?", "八", True),
        ("3+5=?", "答案是8", True),
        ("7-2=?", "5", True),
        ("7-2=?", "三", False),
        ("3+5=?", "答案是吧", True),
        ("3+5=?", "答案是八", True),
        ("天空是什么颜色？", "蓝色", True),
        ("天空是什么颜色？", "蓝", True),
        ("草是什么颜色？", "绿", True),
        ("草是什么颜色？", "红色", False),
        ("1+2=?", "答案是三", True),
        ("1+2=?", "暗示三", True),
        ("1+2=?", "把暗示三。", True),
        ("1+2=?", "一加二是三", True),
    ],
)
def test_validate_answer(question: str, user: str, expect_ok: bool) -> None:
    r = validate_answer(question, user)
    assert r.correct is expect_ok


def test_unknown_question() -> None:
    r = validate_answer("随机未定义题目?", "任意")
    assert r.question_type == "unknown"
    assert r.correct is False
