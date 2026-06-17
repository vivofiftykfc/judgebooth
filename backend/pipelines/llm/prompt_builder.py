"""
组装发送给 LLM 的完整 Prompt。

从 BoothSession 中提取 transcript、fluency_report、emotion_report，
组装为多轮对话消息列表供 LLM API 调用。
"""

from backend.models.session import BoothSession
from backend.pipelines.llm.persona import MUSK_SYSTEM_PROMPT, REVIEW_OUTPUT_SCHEMA


def _build_fluency_summary(fluency: dict | None) -> str:
    """将流畅度报告转换为自然语言段落。"""
    if not fluency:
        return "（流畅度分析数据不可用）"

    wpm = fluency.get("avg_wpm", "N/A")
    pause_count = fluency.get("pause_count", "N/A")
    longest_pause = fluency.get("longest_pause_seconds", "N/A")
    filler_count = fluency.get("filler_word_count", "N/A")
    filler_examples = fluency.get("filler_examples", [])
    stutter = fluency.get("stutter_count", "N/A")
    volatility = fluency.get("wpm_volatility", "N/A")
    summary = fluency.get("summary", "")

    lines = [
        f"平均语速: {wpm} 词/分钟",
        f"停顿次数: {pause_count} 次（最长 {longest_pause} 秒）",
        f"填充词: {filler_count} 次{'（例如：' + '、'.join(filler_examples[:3]) + '）' if filler_examples else ''}",
        f"口吃次数: {stutter} 次",
        f"语速波动率: {volatility}",
        f"综合描述: {summary}",
    ]
    return "\n".join(lines)


def _build_emotion_summary(emotion: dict | None) -> str:
    """将情绪报告转换为自然语言段落。"""
    if not emotion:
        return "（情绪分析数据不可用）"

    tension = emotion.get("tension_index", "N/A")
    smile = emotion.get("smile_index", "N/A")
    overall = emotion.get("overall_emotion", "N/A")
    gaze = emotion.get("gaze_at_camera_pct", "N/A")
    stability = emotion.get("head_stability_score", "N/A")
    summary = emotion.get("summary", "")

    emotion_labels = {
        "relaxed_confident": "放松自信",
        "slightly_nervous": "略显紧张",
        "tense": "紧张",
        "neutral": "中性",
    }

    lines = [
        f"紧张指数: {tension}（0-1，越低越放松）",
        f"微笑指数: {smile}（0-1）",
        f"整体情绪: {emotion_labels.get(overall, overall)}",
        f"注视镜头比例: {gaze}%",
        f"头部稳定性: {stability}（0-100）",
        f"综合描述: {summary}",
    ]
    return "\n".join(lines)


def build_prompt(session: BoothSession) -> list:
    """
    组装 LLM 的多轮对话消息。

    参数:
        session: BoothSession（含 transcript, fluency_report, emotion_report）

    返回:
        [
            {"role": "system", "content": MUSK_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ]
    """
    transcript = session.transcript or "（无转写文本）"
    fluency_summary = _build_fluency_summary(session.fluency_report)
    emotion_summary = _build_emotion_summary(session.emotion_report)

    prompt_text = f"""以下是黑客松参赛者的项目介绍（语音转写文本）：
{transcript}

---

此外，以下是该参赛者在路演过程中的表现分析：

【演讲流畅度】
{fluency_summary}

【情绪与自信度】
{emotion_summary}

---

{REVIEW_OUTPUT_SCHEMA}

请按以下结构输出评审报告：
1. 一句话本质洞察（不超过25字）
2. 2-3个具体的硬核亮点
3. 1个尖锐的第一性原理问题
4. 1-2条可执行的硬核建议
5. 一句结语"""

    return [
        {"role": "system", "content": MUSK_SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text},
    ]
