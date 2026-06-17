"""
视频管线主处理器

编排 CameraCapture → FaceLandmarkerEngine → emotion_analyzer 的完整流程，
对外暴露 session 级别的接口供 PipelineOrchestrator 调用。
"""

import logging
import time

from models.session import BoothSession
from models.performance import EmotionReport

logger = logging.getLogger(__name__)


async def analyze_emotion(session: BoothSession) -> dict | None:
    """视频管线入口：摄像头 → FaceLandmarker → 情绪提取

    参数:
        session: 评审会话（从中读取配置，写入分析结果）

    返回:
        EmotionReport 的 dict 形式，失败返回 None
    """
    try:
        from pipelines.video.camera import CameraCapture
        from pipelines.video.mediapipe_engine import FaceLandmarkerEngine
        from pipelines.video.emotion_analyzer import extract_emotion_signals

        # 1. 初始化摄像头 & 录制
        camera = CameraCapture(index=0)
        try:
            frames = await camera.capture_frames(duration=120, fps=5)
        finally:
            camera.release()

        if not frames:
            session.error = "摄像头未捕获到任何帧"
            return None

        # 保存最佳合影帧
        best_photo = camera.get_best_photo(frames)
        if best_photo is not None:
            # 降采样到 720p 用于分析用副本
            h, w = best_photo.shape[:2]
            if h > 720:
                scale = 720.0 / h
                new_w = int(w * scale)
                new_h = 720
                # 保持原始帧用于分析，保存路径由上层负责
                logger.info("最佳合影帧尺寸: %dx%d, 备选降采样: %dx%d",
                            w, h, new_w, new_h)

        # 2. 初始化 FaceLandmarker
        engine = FaceLandmarkerEngine()
        if not engine.is_ready:
            session.error = "FaceLandmarker 未就绪（模型文件缺失或 mediapipe 未安装）"
            return None

        # 3. 逐帧处理
        frame_features = []
        for i, frame in enumerate(frames):
            timestamp_ms = int(i * (1000 / 5))  # 5fps → 每帧 200ms 间隔
            if i % 30 == 0:
                logger.debug("视频分析进度: %d/%d 帧", i + 1, len(frames))

            # 降采样至 720p 用于分析，提升性能
            h, w = frame.shape[:2]
            if h > 720:
                scale = 720.0 / h
                new_w = int(w * scale)
                analysis_frame = frame  # 保持原帧，mediapipe 内部会处理
            else:
                analysis_frame = frame

            result = engine.process_frame(analysis_frame, timestamp_ms)
            frame_features.append(result)

        # 4. 情绪提取
        signals = extract_emotion_signals(frame_features)

        # 5. 构造 EmotionReport
        report = EmotionReport(
            tension_index=signals.get("tension_index", 0.0),
            smile_index=signals.get("smile_index", 0.0),
            overall_emotion=signals.get("overall_emotion", "neutral"),
            gaze_at_camera_pct=signals.get("gaze_at_camera_pct", 0.0),
            head_stability_score=signals.get("head_stability_score", 0.0),
            summary=signals.get("summary", ""),
        ).model_dump()

        session.emotion_report = report
        logger.info("视频情绪分析完成: %s", report.get("summary", ""))
        return report

    except ImportError as e:
        session.error = f"视频管线模块缺失: {e}"
        return None
    except Exception as e:
        session.error = f"视频分析异常: {e}"
        logger.exception("视频分析异常")
        return None
