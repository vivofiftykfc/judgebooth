from pydantic import BaseModel
from typing import Optional


class FluencyReport(BaseModel):
    """流畅度分析报告（音频后处理产出）"""
    avg_wpm: float
    pause_count: int
    longest_pause_seconds: float
    filler_word_count: int
    filler_examples: list[str]
    stutter_count: int
    wpm_volatility: float
    summary: str


class EmotionReport(BaseModel):
    """情绪指标报告（MediaPipe blendshapes 产出）"""
    tension_index: float            # 0-1
    smile_index: float              # 0-1
    overall_emotion: str            # relaxed_confident | slightly_nervous | tense | neutral
    gaze_at_camera_pct: float       # 0-100
    head_stability_score: float     # 0-100
    summary: str


class PerformanceReport(BaseModel):
    """综合表现分析报告（注入 LLM 用）"""
    fluency: Optional[FluencyReport] = None
    emotion: Optional[EmotionReport] = None
    signal_note: Optional[str] = None  # 降级说明
