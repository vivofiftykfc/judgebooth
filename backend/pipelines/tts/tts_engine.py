"""
Edge TTS 播报引擎（马斯克朗读）。

把评审报告渲染成一段**连贯的口语独白**（不是机械念卡片），中文走中文男声、
穿插的英文句走英文男声，分段合成后拼接成一条 mp3，营造"马斯克当面宣判"的感觉。
"""

import os
import uuid
import logging
import time

import edge_tts

from debug_utils import print_debug, print_step, print_data, print_error, print_file_size

logger = logging.getLogger(__name__)

# backend 根目录（本文件在 backend/pipelines/tts/）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_AUDIO_DIR = os.path.join(_BACKEND_DIR, "data", "audio")

VOICE_ZH = "zh-CN-YunjianNeural"        # 厚实有力的中文男声
VOICE_EN = "en-US-ChristopherNeural"    # 低沉成熟英文男声（马斯克味）
RATE = "+8%"                            # 稍快，更笃定干脆
PITCH_ZH = "-12Hz"                      # 中文降调，更深沉
PITCH_EN = "-3Hz"                       # 英文本就低沉，微降即可


def build_musk_script(review: dict) -> list[tuple[str, str]]:
    """把评审报告组织成连贯独白的分段脚本。

    返回 [(lang, text), ...]，lang ∈ {"zh","en"}。
    英文句放在开场/转折/结尾——最容易被听出是马斯克。
    """
    insight = (review.get("insight") or "").strip()
    highlights = [h for h in (review.get("highlights") or []) if h][:3]
    sharp = (review.get("sharp_question") or "").strip()
    suggestions = [s for s in (review.get("suggestions") or []) if s][:2]
    closing = (review.get("closing") or "").strip()

    seg: list[tuple[str, str]] = []
    # 开场（英文）
    seg.append(("en", "Alright. Let me be brutally honest with you."))
    # 本质洞察
    if insight:
        seg.append(("zh", f"你这个项目，{insight}"))
    # 亮点（串成口语，不报点）
    if highlights:
        seg.append(("zh", "我承认，确实有几个地方还行。" + "。".join(highlights) + "。"))
    # 转折（英文）
    seg.append(("en", "But here's the real question."))
    if sharp:
        seg.append(("zh", sharp))
    # 建议
    if suggestions:
        seg.append(("zh", "想让它真的成，你得这么干。" + "。".join(suggestions) + "。"))
    # 结语
    if closing:
        seg.append(("zh", closing))
    # 收尾（英文，标志性）
    seg.append(("en", "Make it work, or don't bother. Keep going."))
    return seg


async def _tts_segment(text: str, voice: str, pitch: str, retries: int = 2) -> bytes:
    """合成单段语音，带重试；失败返回空字节（不抛）。"""
    for attempt in range(retries):
        try:
            buf = bytearray()
            communicate = edge_tts.Communicate(text, voice, rate=RATE, pitch=pitch)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            if buf:
                return bytes(buf)
        except Exception as e:
            if attempt == retries - 1:
                logger.warning("TTS 段合成失败: %s", e)
    return b""


async def synthesize_musk_speech(review: dict, output_dir: str = _AUDIO_DIR) -> str | None:
    """合成马斯克朗读音频（中英分声 → 拼接成一条 mp3）。失败返回 None。"""
    print_step("TTS", "=== 马斯克朗读合成 ===")
    os.makedirs(output_dir, exist_ok=True)
    script = build_musk_script(review)
    print_data("TTS", "朗读脚本", script)

    t0 = time.time()
    audio = bytearray()
    for lang, text in script:
        if not text:
            continue
        if lang == "en":
            voice, pitch = VOICE_EN, PITCH_EN
        else:
            voice, pitch = VOICE_ZH, PITCH_ZH
        seg = await _tts_segment(text, voice, pitch)
        if seg:
            audio.extend(seg)
        else:
            print_error("TTS", f"段合成失败，跳过: {text[:20]}")

    if not audio:
        print_error("TTS", "TTS 合成结果为空")
        return None

    filename = f"review_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "wb") as f:
        f.write(bytes(audio))

    print_file_size("TTS", output_path)
    print_step("TTS", f"朗读合成完成，耗时 {time.time()-t0:.1f}s（{len(script)} 段）")
    return output_path


# ---- 兼容旧接口（单声道，机械文本）----------------------------------------
async def synthesize_speech(review: dict, output_dir: str = _AUDIO_DIR) -> str | None:
    return await synthesize_musk_speech(review, output_dir)


def render_for_tts(review: dict) -> str:
    """把分段脚本展平成纯文本（供调试/兼容）。"""
    return "".join(t for _, t in build_musk_script(review))
