"""
三管线调度器

编排录音 → 分析（音频/视频/LLM 并行）→ 输出（合影/QR）的完整流程。
每个阶段通过 SSE 推送进度，所有错误被捕获到 session.error 而非崩溃。

设计要点:
  - start_recording() 同时启动音视频录制（非先后）
  - analyze() 同时停止音视频，然后并行分析已采集的数据
  - 分析管线不再重新录制，直接用已采集的数据
"""

import asyncio
import time
from collections.abc import Callable, Coroutine
from typing import Any

from models.session import BoothSession
from debug_utils import print_debug, print_step, print_data, print_error, print_file_size


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
    # 1. Recording — 同时录制音视频，fire-and-forget
    # ------------------------------------------------------------------
    async def start_recording(self) -> None:
        """启动录音（前端负责传视频帧）。"""
        print_step("ORCH", "=== 启动音频录制 ===")

        async def _record_audio():
            t0 = time.time()
            try:
                from pipelines.audio.recorder import record_audio

                from config import AUDIO_DURATION
                print_debug("ORCH", f"开始录音({AUDIO_DURATION}s) — 用户可 End Early 提前结束")
                audio_path = await record_audio(duration=AUDIO_DURATION, sample_rate=16000)
                self.session.audio_path = audio_path
                print_debug("ORCH", f"录音完成，耗时 {time.time()-t0:.1f}s")

            except ImportError as e:
                self.session.error = f"录音模块不可用: {e}"
                print_error("ORCH", f"录音模块不可用: {e}")
                await self._do_notify()
            except Exception as exc:
                self.session.error = f"录音异常: {exc}"
                print_error("ORCH", f"录音异常: {exc}")
                await self._do_notify()

        self._recording_task = asyncio.create_task(_record_audio())

    # ------------------------------------------------------------------
    # 2. Analysis — 停止录制 → 并行分析已采集的数据
    # ------------------------------------------------------------------
    async def analyze(self) -> None:
        """停止录音+录像，并行分析已采集的数据（不再重新录制）。"""
        print_step("ORCH", "=== 停止录制 + 开始分析 ===")

        # 先停止录制（保存已录的数据）
        if self._recording_task and not self._recording_task.done():
            print_debug("ORCH", "停止录音和录像...")
            try:
                # 停止录音（保留已采集的音频帧）
                from pipelines.audio.recorder import stop_recording
                await stop_recording()
                print_debug("ORCH", "录音已停止")
            except Exception as e:
                print_error("ORCH", f"停止录音异常: {e}")

            # 等待录制任务完成收尾
            try:
                await asyncio.wait_for(self._recording_task, timeout=5.0)
            except asyncio.TimeoutError:
                print_error("ORCH", "录制任务超时未完成，强制取消")
                self._recording_task.cancel()
            except Exception as e:
                print_error("ORCH", f"等待录制任务完成时异常: {e}")

            self._recording_task = None
            print_debug("ORCH", "录制任务已结束")

        # 日志：已采集的数据
        print_data("ORCH", "audio_path", self.session.audio_path)
        frame_count = len(self.session.video_frames) if self.session.video_frames else 0
        print_data("ORCH", "前端传过来的视频帧数", frame_count)

        # 并行分析管线
        async def _audio():
            t0 = time.time()
            print_step("ORCH", "--- 音频管线启动 ---")
            try:
                from pipelines.audio.processor import analyze_fluency

                self.session.fluency_report = await analyze_fluency(self.session)
                elapsed = time.time() - t0
                print_debug("ORCH", f"音频管线完成，耗时 {elapsed:.1f}s")
                print_data("ORCH", "fluency_report", self.session.fluency_report)
            except Exception as exc:
                self.session.error = f"音频分析异常: {exc}"
                print_error("ORCH", f"音频分析异常: {exc}")
            await self._do_notify()

        async def _video():
            t0 = time.time()
            print_step("ORCH", "--- 视频管线启动 ---")
            try:
                from pipelines.video.processor import analyze_emotion

                self.session.emotion_report = await analyze_emotion(self.session)
                elapsed = time.time() - t0
                print_debug("ORCH", f"视频管线完成，耗时 {elapsed:.1f}s")
                print_data("ORCH", "emotion_report", self.session.emotion_report)
            except Exception as exc:
                self.session.error = f"视频分析异常: {exc}"
                print_error("ORCH", f"视频分析异常: {exc}")
            await self._do_notify()

        async def _llm():
            t0 = time.time()
            print_step("ORCH", "--- LLM 管线启动 ---")
            try:
                from pipelines.llm.llm_engine import generate_review

                self.session.review = await generate_review(self.session)
                elapsed = time.time() - t0
                print_debug("ORCH", f"LLM 管线完成，耗时 {elapsed:.1f}s")
                print_data("ORCH", "review", self.session.review)
            except Exception as exc:
                self.session.error = f"LLM 评审异常: {exc}"
                print_error("ORCH", f"LLM 评审异常: {exc}")
            await self._do_notify()

        async def _run_all():
            print_debug("ORCH", "三管线并行分析已采集的数据...")
            t0 = time.time()
            await asyncio.gather(_audio(), _video(), _llm(), return_exceptions=True)
            total = time.time() - t0
            print_step("ORCH", f"=== 三管线全部完成，总耗时 {total:.1f}s ===")
            print_data("ORCH", "合并错误", self.session.error)

            # 生成马斯克朗读音频（评审就绪后，进 reviewing 前；失败不阻断）
            if self.session.review:
                try:
                    from pipelines.tts.tts_engine import synthesize_musk_speech
                    audio_path = await synthesize_musk_speech(self.session.review)
                    self.session.review_audio_path = audio_path
                    print_data("ORCH", "朗读音频", audio_path)
                except Exception as exc:
                    print_error("ORCH", f"朗读合成异常（降级，不阻断）: {exc}")

            # 自动推进到 reviewing（Thinking 页面会自动因为 SSE 跳转）
            print_step("ORCH", "自动推进: thinking → reviewing")
            self.session.step = "reviewing"
            await self._do_notify()

        asyncio.create_task(_run_all())

    # ------------------------------------------------------------------
    # 3. Output — photo + QR + H5
    # ------------------------------------------------------------------
    async def generate_output(self) -> None:
        """生成合影、二维码和 H5 页面。"""
        print_step("ORCH", "=== 输出生成 ===")

        async def _generate():
            t0 = time.time()
            try:
                from pipelines.output.photo_composer import compose_photo
                from pipelines.output.qr_generator import generate_qr
                from pipelines.output.h5_generator import generate_h5

                # 提前保存快照（AI 生图太久，session 可能被重置）
                snapshot = {
                    "review": dict(self.session.review or {}),
                    "fluency": dict(self.session.fluency_report or {}),
                    "emotion": dict(self.session.emotion_report or {}),
                }

                print_debug("ORCH", "开始生成二维码（合影需要嵌入）...")
                qr = await generate_qr(self.session)
                self.session.qr_path = qr
                print_file_size("ORCH", qr)
                await self._do_notify()

                print_debug("ORCH", "开始合成合影（嵌入二维码）...")
                photo = await compose_photo(
                    camera_best_photo_path=self.session.photo_path,
                    review=self.session.review,
                    qr_path=self.session.qr_path,
                )
                self.session.photo_path = photo
                print_file_size("ORCH", photo)
                await self._do_notify()

                print_debug("ORCH", "开始生成 H5 页面（用快照数据）...")
                h5_path = await generate_h5(self.session, snapshot_data=snapshot)
                print_file_size("ORCH", h5_path)

                elapsed = time.time() - t0
                print_step("ORCH", f"=== 输出生成全部完成，耗时 {elapsed:.1f}s ===")
            except ImportError as e:
                self.session.error = "输出模块不可用（部分管线尚未构建）"
                print_error("ORCH", f"输出模块导入失败: {e}")
            except Exception as exc:
                self.session.error = f"输出生成异常: {exc}"
                print_error("ORCH", f"输出生成异常: {exc}")
            await self._do_notify()

        asyncio.create_task(_generate())
