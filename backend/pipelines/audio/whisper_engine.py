"""
Whisper 转写客户端

使用本地 faster-whisper 模型进行语音转写。
faster-whisper 基于 CTranslate2，速度比原版 openai-whisper 快 3-4 倍。

典型用法:
    result = await transcribe("/path/to/audio.wav")
"""

import logging
from pathlib import Path

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
        return None

    try:
        from faster_whisper import WhisperModel

        global _MODEL
        if _MODEL is None:
            logger.info("加载 faster-whisper small 模型（首次加载较慢）...")
            _MODEL = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("模型加载完成")

        segments, info = _MODEL.transcribe(
            str(audio_path),
            language="zh",
            beam_size=3,
            vad_filter=True,
        )

        full_text = ""
        segment_list = []
        for seg in segments:
            full_text += seg.text
            segment_list.append({
                "text": seg.text.strip(),
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "confidence": round(seg.avg_logprob, 3),
            })

        if not full_text.strip() and not segment_list:
            return _empty_result()

        return {
            "text": full_text.strip(),
            "segments": segment_list,
            "language": info.language or "zh",
        }

    except ImportError:
        logger.warning("faster-whisper 未安装，尝试使用 openai-whisper 备用")
        return await _transcribe_fallback(audio_path)
    except Exception as e:
        logger.error("faster-whisper 转写失败: %s", e)
        return await _transcribe_fallback(audio_path)


async def _transcribe_fallback(audio_path: str) -> dict | None:
    """备用方案：使用原版 openai-whisper。"""
    try:
        import whisper
    except ImportError:
        logger.error("openai-whisper 也未安装，无可用转写引擎")
        return None

    try:
        model = whisper.load_model("small")
        result = model.transcribe(
            audio_path, language="zh", task="transcribe", beam_size=3, vad_filter=True,
        )
    except Exception as e:
        logger.error("openai-whisper 备用转写失败: %s", e)
        return None

    text = (result.get("text") or "").strip()
    segments = result.get("segments", [])

    if not text and not segments:
        return _empty_result()

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
