"""HTTP 响应模型。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VerifyResponse(BaseModel):
    status: str = Field(..., description="success 或错误码")
    recognized_text: str = ""
    answer_correct: Optional[bool] = Field(
        None, description="校验结果；题目非法时可为 null"
    )
    question_type: str = ""
    expected_answer: str = ""
    message: str = ""
    audio_meta: Dict[str, Any] = Field(default_factory=dict)
    detail_log: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "ai-asr"
    whisper_model: str = ""
    asr_engine: str = Field("", description="funasr 或 whisper（含自动回退）")
    funasr_model: Optional[str] = Field(None, description="FunASR 模型名，非 FunASR 时为 null")
