"""
Edge TTS 播报引擎。

将评审报告的 5 段内容合成为语音播报音频。
使用 edge_tts 库调用微软 Edge TTS 服务。
"""

import os
import uuid
import logging

import edge_tts

logger = logging.getLogger(__name__)

VOICE = "zh-CN-YunxiNeural"  # 沉稳男声


async def synthesize_speech(
    review: dict,
    output_dir: str = "D:/hks/backend/data/audio",
) -> str:
    """
    将评审报告 5 段合成语音。

    逻辑:
    1. 将 review dict 展平为 TTS 文本（见 render_for_tts）
    2. 调用 edge_tts.Communicate(text, VOICE).save(output_path)
    3. 返回音频文件路径

    参数:
        review: 评审报告 dict（含 insight, highlights, sharp_question, suggestions, closing）
        output_dir: 输出目录

    返回:
        生成的音频文件绝对路径
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"review_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join(output_dir, filename)

    text = render_for_tts(review)

    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)

    logger.info("TTS 音频已生成: %s", output_path)
    return output_path


def render_for_tts(review: dict) -> str:
    """
    将 review dict 转成适合 TTS 朗读的文本。

    格式:
    "好，我看完了。
    一句话：{insight}
    说几个亮点：第一，{h1}。第二，{h2}。
    但是我要问一个尖锐的问题：{sharp_question}
    我建议：{suggestions}
    最后：{closing}"
    """
    insight = review.get("insight", "")
    highlights = review.get("highlights", [])
    sharp_question = review.get("sharp_question", "")
    suggestions = review.get("suggestions", [])
    closing = review.get("closing", "")

    parts = ["好，我看完了。"]

    if insight:
        parts.append(f"一句话：{insight}")

    if highlights:
        highlight_text = "说几个亮点：" + "。".join(
            f"第一，{highlights[0]}" if i == 0
            else f"第{'二' if i == 1 else '三'}，{h}"
            for i, h in enumerate(highlights[:3])
        )
        parts.append(highlight_text)

    if sharp_question:
        parts.append(f"但是我要问一个尖锐的问题：{sharp_question}")

    if suggestions:
        suggestions_text = "我建议：" + "。".join(
            f"第{'一' if i == 0 else '二'}条，{s}"
            for i, s in enumerate(suggestions[:2])
        )
        parts.append(suggestions_text)

    if closing:
        parts.append(f"最后：{closing}")

    return "。".join(parts)
