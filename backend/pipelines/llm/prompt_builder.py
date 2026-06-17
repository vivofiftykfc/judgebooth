"""
组装发送给 LLM 的完整 Prompt。

从 BoothSession 中提取 transcript、fluency_report、emotion_report，
组装为多轮对话消息列表供 LLM API 调用。
"""

from models.session import BoothSession
from pipelines.llm.persona import MUSK_SYSTEM_PROMPT, REVIEW_OUTPUT_SCHEMA
from debug_utils import print_debug, print_step, print_data, print_error

# 高质量示例，用来锚定"语气 + 颗粒度"（不照抄内容，只学风格）
REVIEW_EXAMPLE = """参考示例（项目：用 AI 给外卖订单自动派单、优化配送路径）：
{
  "insight": "你在给一个已经解决的问题，造第三个轮子。",
  "highlights": ["真接了实时路况 API，不是写死的假数据", "自己实现了贪心+模拟退火的调度，是动了手的"],
  "sharp_question": "美团饿了么的派单系统迭代了十年，你凭什么更优？你的算法到 1 万单还跑得动吗？",
  "suggestions": ["别和巨头拼通用派单，找一个他们看不上的垂直场景（园区、医院送检）", "把模拟退火换成可解释的规则+局部搜索，现场出问题你能调"],
  "closing": "技术不差，方向危险。换个战场，继续干。"
}"""


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
    print_step("PROMPT", "=== 组装 LLM Prompt ===")
    transcript = session.transcript or "（无转写文本）"
    fluency_summary = _build_fluency_summary(session.fluency_report)
    emotion_summary = _build_emotion_summary(session.emotion_report)

    print_data("PROMPT", "transcript 前100字", transcript[:100])
    print_data("PROMPT", "fluency_report 是否存在", session.fluency_report is not None)
    print_data("PROMPT", "emotion_report 是否存在", session.emotion_report is not None)

    prompt_text = f"""以下是黑客松参赛者的项目介绍（语音转写文本）：
{transcript}

---

以下是该参赛者在路演过程中的表现分析（请把它当评审弹药，在能支撑判断时引用一次，别堆数据）：

【演讲流畅度】
{fluency_summary}

【情绪与自信度】
{emotion_summary}

---

{REVIEW_EXAMPLE}

---

{REVIEW_OUTPUT_SCHEMA}

要求：
- 用马斯克的口吻：短句、结论先行、对抗性、可带黑色幽默；不要客气的 AI 味。
- 亮点必须具体到技术/工程细节；尖锐问题要直击"这项目能不能成立"。
- 若转写文本几乎为空或听不出在做什么，就直接在 insight 里点破"我没听到任何工程"，不要编造亮点。
- 只输出 JSON，全中文，insight ≤ 25 字。"""

    total_len = len(prompt_text) + len(MUSK_SYSTEM_PROMPT)
    print_debug("PROMPT", f"Prompt 总长度: ~{total_len} 字符")

    return [
        {"role": "system", "content": MUSK_SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text},
    ]
