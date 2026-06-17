"""
三管线调度器

编排录音 → 分析（音频/视频/LLM 并行）→ 输出（合影/QR）的完整流程。
每个阶段通过 SSE 推送进度，所有错误被捕获到 session.error 而非崩溃。
"""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from models.session import BoothSession


class PipelineOrchestrator:
    """Three-pipeline scheduler for the review booth session."""

    def __init__(
        self,
        session: BoothSession,
        notify: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ):
        self.session = session
        self._notify = notify
        self._recording_task: asyncio.Task | None = None

    async def _do_notify(self) -> None:
        if self._notify is not None:
            try:
                await self._notify()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 1. Recording — fire-and-forget, auto-stops after 120s
    # ------------------------------------------------------------------
    async def start_recording(self) -> None:
        """启动录音和录像（并行运行，120s 后自动停止）。"""

        async def _record_both():
            try:
                from pipelines.audio.recorder import record_audio

                audio_path = await record_audio(duration=120, sample_rate=16000)
                self.session.audio_path = audio_path
            except ImportError:
                self.session.error = "录音模块不可用"
                await self._do_notify()
            except Exception as exc:
                self.session.error = f"录音异常: {exc}"
                await self._do_notify()

        self._recording_task = asyncio.create_task(_record_both())

    # ------------------------------------------------------------------
    # 2. Analysis — 3 pipelines run in parallel
    # ------------------------------------------------------------------
    async def analyze(self) -> None:
        """停止录音，并行运行三条分析管线。"""

        # Cancel recording if still running
        if self._recording_task and not self._recording_task.done():
            self._recording_task.cancel()
            try:
                await self._recording_task
            except asyncio.CancelledError:
                pass
            self._recording_task = None

        async def _audio():
            try:
                from pipelines.audio.processor import analyze_fluency

                self.session.fluency_report = await analyze_fluency(self.session)
            except Exception as exc:
                self.session.error = f"音频分析异常: {exc}"
            await self._do_notify()

        async def _video():
            try:
                from pipelines.video.processor import analyze_emotion

                self.session.emotion_report = await analyze_emotion(self.session)
            except Exception as exc:
                self.session.error = f"视频分析异常: {exc}"
            await self._do_notify()

        async def _llm():
            try:
                from pipelines.llm.llm_engine import generate_review

                self.session.review = await generate_review(self.session)
            except Exception as exc:
                self.session.error = f"LLM 评审异常: {exc}"
            await self._do_notify()

        async def _run_all():
            await asyncio.gather(_audio(), _video(), _llm(), return_exceptions=True)

        asyncio.create_task(_run_all())

    # ------------------------------------------------------------------
    # 3. Output — photo + QR
    # ------------------------------------------------------------------
    async def generate_output(self) -> None:
        """生成合影、二维码和 H5 页面。"""

        async def _generate():
            try:
                from pipelines.output.photo_composer import compose_photo
                from pipelines.output.qr_generator import generate_qr
                from pipelines.output.h5_generator import generate_h5

                photo = await compose_photo(self.session)
                self.session.photo_path = photo

                qr = await generate_qr(self.session)
                self.session.qr_path = qr

                await generate_h5(self.session)
            except ImportError:
                self.session.error = "输出模块不可用（部分管线尚未构建）"
            except Exception as exc:
                self.session.error = f"输出生成异常: {exc}"
            await self._do_notify()

        asyncio.create_task(_generate())
