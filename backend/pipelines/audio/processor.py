"""
音频管线主处理器

编排 recorder → whisper_engine → fluency_analyzer 的完整流程，
对外暴露 session 级别的接口供 PipelineOrchestrator 调用。
"""

from models.session import BoothSession
from models.performance import FluencyReport


async def analyze_fluency(session: BoothSession) -> dict | None:
    """音频管线入口：录音 → 转写 → 流畅度分析

    参数:
        session: 评审会话（从中读取配置，写入分析结果）

    返回:
        FluencyReport 的 dict 形式，失败返回 None
    """
    try:
        from pipelines.audio.recorder import record_audio
        from pipelines.audio.whisper_engine import transcribe
        from pipelines.audio.fluency_analyzer import analyze_fluency as _calc

        # 1. 录音
        audio_path = await record_audio(duration=120, sample_rate=16000)
        session.audio_path = audio_path

        # 2. 转写
        whisper_result = await transcribe(audio_path)
        if whisper_result is None:
            session.error = "语音转写失败（Whisper 服务不可用）"
            return None

        session.transcript = whisper_result.get("text", "")

        # 3. 流畅度分析
        segments = whisper_result.get("segments", [])
        metrics = _calc(segments)
        metrics["summary"] = _generate_summary(metrics)

        report = FluencyReport(
            avg_wpm=metrics.get("avg_wpm", 0),
            pause_count=metrics.get("pause_count", 0),
            longest_pause_seconds=metrics.get("longest_pause_seconds", 0),
            filler_word_count=metrics.get("filler_word_count", 0),
            filler_examples=metrics.get("filler_examples", []),
            stutter_count=metrics.get("stutter_count", 0),
            wpm_volatility=metrics.get("wpm_volatility", 0),
            summary=metrics.get("summary", ""),
        ).model_dump()

        session.fluency_report = report
        return report

    except ImportError as e:
        session.error = f"音频管线模块缺失: {e}"
        return None
    except Exception as e:
        session.error = f"音频分析异常: {e}"
        return None


def _generate_summary(metrics: dict) -> str:
    """从指标生成一句话概述"""
    parts = []
    wpm = metrics.get("avg_wpm", 0)
    if wpm < 100:
        parts.append(f"语速偏慢（{wpm:.0f}词/分钟）")
    elif wpm < 140:
        parts.append(f"语速适中偏慢（{wpm:.0f}词/分钟）")
    elif wpm < 200:
        parts.append(f"语速适中（{wpm:.0f}词/分钟）")
    else:
        parts.append(f"语速偏快（{wpm:.0f}词/分钟）")

    pause = metrics.get("pause_count", 0)
    if pause > 10:
        parts.append(f"出现{pause}次停顿")

    filler = metrics.get("filler_word_count", 0)
    if filler > 5:
        examples = "、".join(set(metrics.get("filler_examples", [])))
        parts.append(f"使用{filler}次口头禅（如{examples}）")

    return "，".join(parts) if parts else "流畅度正常"
