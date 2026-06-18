"""
音频管线主处理器

编排 recorder → whisper_engine → fluency_analyzer 的完整流程，
对外暴露 session 级别的接口供 PipelineOrchestrator 调用。
"""

import os
import time

from models.session import BoothSession
from models.performance import FluencyReport
from debug_utils import print_debug, print_step, print_data, print_error, print_file_size


async def analyze_fluency(session: BoothSession) -> dict | None:
    """音频管线入口：录音 → 转写 → 流畅度分析

    参数:
        session: 评审会话（从中读取配置，写入分析结果）

    返回:
        FluencyReport 的 dict 形式，失败返回 None
    """
    t_pipeline = time.time()
    print_step("AUDIO", "=== 音频管线启动 ===")
    try:
        from pipelines.audio.recorder import record_audio
        from pipelines.audio.whisper_engine import transcribe
        from pipelines.audio.fluency_analyzer import analyze_fluency as _calc

        # 0. 优先用前端 Soniox 实时转写（已带词级时间戳）→ 跳过录音 + whisper
        if session.transcript is not None and session.transcript_segments is not None:
            print_step("AUDIO", ">> 使用前端 Soniox 实时转写（跳过录音 + Whisper）")
            print_data("AUDIO", "Soniox 转写文本", session.transcript)
            segments = session.transcript_segments
            metrics = _calc(segments)
            metrics["summary"] = _generate_summary(metrics)
            print_data("AUDIO", "流畅度指标", metrics)
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
            print_step("AUDIO", f"=== 音频管线完成（Soniox），总耗时 {time.time()-t_pipeline:.1f}s ===")
            return report

        # 1. 录音（仅当还没录过时）—— Soniox 不可用时的离线兜底
        if session.audio_path and os.path.isfile(session.audio_path):
            audio_path = session.audio_path
            print_debug("AUDIO", f"使用已有录音: {audio_path}")
            print_file_size("AUDIO", audio_path)
        else:
            print_step("AUDIO", ">> 录音阶段（10s，路演已结束，只需采集用户刚才说的内容）")
            t0 = time.time()
            # 此时用户已结束路演，只录 10s 就够了（正常应在 presenting 阶段录完）
            audio_path = await record_audio(duration=60, sample_rate=16000)
            session.audio_path = audio_path
            print_debug("AUDIO", f"录音完成，耗时 {time.time()-t0:.1f}s")
            print_file_size("AUDIO", audio_path)

        # 2. 转写
        print_step("AUDIO", ">> Whisper 转写阶段")
        t0 = time.time()
        whisper_result = await transcribe(audio_path)
        print_debug("AUDIO", f"转写完成，耗时 {time.time()-t0:.1f}s")
        if whisper_result is None:
            session.error = "语音转写失败（Whisper 服务不可用）"
            print_error("AUDIO", "Whisper 转写返回 None")
            return None

        session.transcript = whisper_result.get("text", "")
        print_data("AUDIO", "转写文本", session.transcript)
        print_data("AUDIO", "片段数", whisper_result.get("segments", []))
        print_debug("AUDIO", f"检测语言: {whisper_result.get('language', '?')}")

        # 3. 流畅度分析
        print_step("AUDIO", ">> 流畅度分析阶段")
        t0 = time.time()
        segments = whisper_result.get("segments", [])
        metrics = _calc(segments)
        metrics["summary"] = _generate_summary(metrics)
        print_debug("AUDIO", f"流畅度分析完成，耗时 {time.time()-t0:.2f}s")
        print_data("AUDIO", "流畅度指标", metrics)

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
        print_step("AUDIO", f"=== 音频管线完成，总耗时 {time.time()-t_pipeline:.1f}s ===")
        return report

    except ImportError as e:
        session.error = f"音频管线模块缺失: {e}"
        print_error("AUDIO", f"模块缺失: {e}")
        return None
    except Exception as e:
        session.error = f"音频分析异常: {e}"
        print_error("AUDIO", f"异常: {e}")
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
