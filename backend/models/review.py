from pydantic import BaseModel
from typing import Optional


class ReviewReport(BaseModel):
    """5段式评审报告"""
    insight: str                    # 一句话本质洞察（≤25字）
    highlights: list[str]           # 2-3个硬核亮点
    sharp_question: str             # 1个尖锐问题
    suggestions: list[str]          # 1-2条硬核建议
    closing: str                    # 一句结语


class ReviewResponse(BaseModel):
    """LLM 评审 API 响应"""
    review: ReviewReport
    raw_text: Optional[str] = None
