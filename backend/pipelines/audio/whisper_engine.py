"""
Whisper 转写客户端

使用本地 faster-whisper 模型进行语音转写。
faster-whisper 基于 CTranslate2，速度比原版 openai-whisper 快 3-4 倍。

典型用法:
    result = await transcribe("/path/to/audio.wav")
"""

import logging
from pathlib import Path

from debug_utils import print_debug, print_step, print_error

logger = logging.getLogger(__name__)

# 全局缓存模型，避免重复加载
_MODEL = None


async def transcribe(audio_path: str) -> dict | None:
    """
    使用本地 faster-whisper 转写音频文件。

    参数:
        audio_path: WAV 文件路径

    返回:
        {
            "text": "完整转写文本",
            "segments": [
                {"text": "段落", "start": 0.5, "end": 1.2, "confidence": 0.95},
                ...
            ],
            "language": "zh"
        }
        失败返回 None
    """
    audio_path_obj = Path(audio_path)
    if not audio_path_obj.exists():
        logger.error("音频文件不存在: %s", audio_path)
        print_error("WHISPER", f"音频文件不存在: {audio_path}")
        return None

    try:
        from faster_whisper import WhisperModel

        global _MODEL
        if _MODEL is None:
            print_step("WHISPER", "加载 faster-whisper small 模型（首次下载约 20s）...")
            _MODEL = WhisperModel("small", device="cpu", compute_type="int8")
            print_debug("WHISPER", "faster-whisper 模型加载完成")

        print_step("WHISPER", f"开始转写: {audio_path}")
        import time
        t0 = time.time()
        segments, info = _MODEL.transcribe(
            str(audio_path),
            language="zh",
            beam_size=3,
            vad_filter=True,
        )
        print_debug("WHISPER", f"转写 API 调用完成，耗时 {time.time()-t0:.1f}s")
        print_debug("WHISPER", f"检测语言: {info.language}, 概率: {info.language_probability:.2f}")

        full_text = ""
        segment_list = []
        seg_count = 0
        for seg in segments:
            full_text += seg.text
            segment_list.append({
                "text": seg.text.strip(),
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "confidence": round(seg.avg_logprob, 3),
            })
            seg_count += 1

        print_debug("WHISPER", f"转写完成: {seg_count} 个片段, 总字符数 {len(full_text)}")

        if not full_text.strip() and not segment_list:
            print_debug("WHISPER", "转写结果为空，返回空结果")
            return _empty_result()

        return {
            "text": full_text.strip(),
            "segments": segment_list,
            "language": info.language or "zh",
        }

    except ImportError:
        logger.warning("faster-whisper 未安装，尝试使用 openai-whisper 备用")
        print_debug("WHISPER", "faster-whisper 未安装，尝试 openai-whisper 备用")
        return await _transcribe_fallback(audio_path)
    except Exception as e:
        logger.error("faster-whisper 转写失败: %s", e)
        print_error("WHISPER", f"faster-whisper 转写失败: {e}")
        return await _transcribe_fallback(audio_path)


async def _transcribe_fallback(audio_path: str) -> dict | None:
    """备用方案：使用原版 openai-whisper。"""
    try:
        import whisper
    except ImportError:
        logger.error("openai-whisper 也未安装，无可用转写引擎")
        print_error("WHISPER", "openai-whisper 也未安装，无可用转写引擎")
        return None

    try:
        print_debug("WHISPER", "加载 openai-whisper 模型...")
        model = whisper.load_model("small")
        print_debug("WHISPER", "开始 openai-whisper 转写...")
        result = model.transcribe(
            audio_path, language="zh", task="transcribe", beam_size=3, vad_filter=True,
        )
        print_debug("WHISPER", "openai-whisper 转写完成")
    except Exception as e:
        logger.error("openai-whisper 备用转写失败: %s", e)
        print_error("WHISPER", f"openai-whisper 转写失败: {e}")
        return None

    text = (result.get("text") or "").strip()
    segments = result.get("segments", [])

    if not text and not segments:
        print_debug("WHISPER", "openai-whisper 转写结果为空")
        return _empty_result()

    print_debug("WHISPER", f"openai-whisper 转写: {len(text)} 字符, {len(segments)} 片段")
    return {
        "text": text,
        "segments": [
            {
                "text": seg.get("text", "").strip(),
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
                "confidence": float(seg.get("confidence", 0) or seg.get("avg_logprob", 0)),
            }
            for seg in segments
        ],
        "language": result.get("language", "zh"),
    }


def _empty_result() -> dict:
    return {"text": "", "segments": [], "language": "zh"}
