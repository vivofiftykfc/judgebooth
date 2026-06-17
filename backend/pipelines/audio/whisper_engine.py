"""
Whisper 转写客户端

提供两层转写策略:
  1. 主方案: 调用 docker-whisper-live REST API (http://localhost:9090)
  2. 备用方案: 使用本地 openai-whisper 模型直接转写

典型用法:
    result = await transcribe("/path/to/audio.wav")
    if result is None:
        result = await transcribe_fallback("/path/to/audio.wav")
"""

import asyncio
from pathlib import Path

import httpx

from backend.config import WHISPER_URL

WHISPER_API_URL = f"{WHISPER_URL}/transcribe"
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 3
RETRY_DELAY = 2.0


async def transcribe(audio_path: str) -> dict | None:
    """
    上传 WAV 文件到 whisper-live 服务，获取转写结果。

    参数:
        audio_path: 本地 WAV 文件路径

    返回:
        转写结果字典，包含 text、segments、language 字段；
        若全部重试失败则返回 None。

    返回格式:
        {
            "text": "完整转写文本",
            "segments": [
                {
                    "text": "段落文本",
                    "start": 0.5,
                    "end": 1.2,
                    "confidence": 0.95
                },
                ...
            ],
            "language": "zh"
        }

    错误处理:
        - 连接 / 超时错误重试最多 3 次 (间隔 2s)
        - 全部失败后返回 None，由调用方决定是否降级
        - 若响应中 text 为空或所有 segment confidence 均 < 0.3，
          视为低质量结果，返回空结构
    """
    audio_path_obj = Path(audio_path)
    if not audio_path_obj.exists():
        return None

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                with open(audio_path, "rb") as f:
                    files = {"file": (audio_path_obj.name, f, "audio/wav")}
                    response = await client.post(WHISPER_API_URL, files=files)

                response.raise_for_status()
                data = response.json()

                # 校验响应结构
                text = data.get("text", "").strip()
                segments = data.get("segments", [])

                if not text and not segments:
                    return _empty_result()

                # 低质量检测: 所有 segment 的置信度都低于 0.3
                if segments and all(
                    seg.get("confidence", 0) is not None and seg.get("confidence", 0) < 0.3
                    for seg in segments
                ):
                    return _empty_result()

                # 确保每个 segment 有完整的字段
                normalized = {
                    "text": text,
                    "segments": [
                        {
                            "text": seg.get("text", ""),
                            "start": float(seg.get("start", 0)),
                            "end": float(seg.get("end", 0)),
                            "confidence": float(seg.get("confidence", 0)),
                        }
                        for seg in segments
                    ],
                    "language": data.get("language", "zh"),
                }
                return normalized

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
        except httpx.HTTPStatusError as e:
            # 服务端返回 4xx/5xx — 不重试，直接失败
            return None

    # 所有重试均失败
    return None


async def transcribe_fallback(audio_path: str) -> dict | None:
    """
    备用转写方案。

    当 docker-whisper-live 服务不可用时，尝试使用本地
    openai-whisper 模型直接转写。

    参数:
        audio_path: 本地 WAV 文件路径

    返回:
        与 transcribe() 相同结构的字典；若 whisper 库未安装或
        转写失败则返回 None。
    """
    try:
        import whisper
    except ImportError:
        return None

    try:
        model = whisper.load_model("small")
        result = model.transcribe(
            audio_path,
            language="zh",
            task="transcribe",
            beam_size=3,
            vad_filter=True,
        )
    except Exception:
        return None

    text = (result.get("text") or "").strip()
    segments = result.get("segments", [])

    if not text and not segments:
        return _empty_result()

    return {
        "text": text,
        "segments": [
            {
                "text": seg.get("text", ""),
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
                "confidence": float(seg.get("confidence", 0) or seg.get("avg_logprob", 0)),
            }
            for seg in segments
        ],
        "language": result.get("language", "zh"),
    }


def _empty_result() -> dict:
    """返回一个空结果结构，便于调用方统一处理。"""
    return {
        "text": "",
        "segments": [],
        "language": "zh",
    }
