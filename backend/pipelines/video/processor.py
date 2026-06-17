"""
视频管线主处理器

从前端浏览器传来的 Base64 JPEG 帧 → FaceLandmarkerEngine → emotion_analyzer，
对外暴露 session 级别的接口供 PipelineOrchestrator 调用。
"""

import base64
import logging
import os
import time
import uuid
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from models.session import BoothSession
from models.performance import EmotionReport
from debug_utils import print_debug, print_step, print_data, print_error, print_file_size

logger = logging.getLogger(__name__)


def _base64_to_cv2(base64_str: str) -> np.ndarray | None:
    """将 Base64 JPEG 字符串转为 OpenCV BGR numpy 数组。"""
    try:
        # 去掉 data:image/jpeg;base64, 前缀（如果有）
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        img_data = base64.b64decode(base64_str)
        np_arr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except Exception as e:
        print_error("VIDEO", f"Base64 解码失败: {e}")
        return None


async def analyze_emotion(session: BoothSession) -> dict | None:
    """视频管线入口：前端帧 → FaceLandmarker → 情绪提取

    参数:
        session: 评审会话（含前端传来的 Base64 视频帧列表）

    返回:
        EmotionReport 的 dict 形式，失败返回 None
    """
    t_pipeline = time.time()
    print_step("VIDEO", "=== 视频管线启动 ===")
    try:
        from pipelines.video.mediapipe_engine import FaceLandmarkerEngine
        from pipelines.video.emotion_analyzer import extract_emotion_signals

        # 1. 获取帧列表
        raw_frames = session.video_frames or []
        if not raw_frames:
            session.error = "前端没有传视频帧过来（摄像头可能被拒绝）"
            print_error("VIDEO", "video_frames 为空，前端可能没有传帧")
            return None

        print_debug("VIDEO", f"前端传来 {len(raw_frames)} 帧，解码中...")

        # 2. 解码 Base64 → OpenCV 图像
        t0 = time.time()
        frames = []
        first_frame = None
        for i, b64 in enumerate(raw_frames):
            frame = _base64_to_cv2(b64)
            if frame is not None:
                frames.append(frame)
                if first_frame is None:
                    first_frame = frame

        elapsed = time.time() - t0
        print_debug("VIDEO", f"解码完成: {len(frames)} 帧有效，耗时 {elapsed:.2f}s")

        if not frames:
            session.error = "所有前端帧解码失败"
            print_error("VIDEO", "所有帧解码失败")
            return None

        # 3. 保存第一帧作为最佳合影帧
        if first_frame is not None:
            h, w = first_frame.shape[:2]
            print_debug("VIDEO", f"第一帧尺寸: {w}x{h}")
            photo_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "photos")
            os.makedirs(photo_dir, exist_ok=True)
            best_frame_path = os.path.join(photo_dir, f"best_frame_{uuid.uuid4().hex[:8]}.jpg")
            cv2.imwrite(best_frame_path, first_frame)
            session.photo_path = best_frame_path
            print_debug("VIDEO", f"最佳帧已保存: {best_frame_path}")
            print_file_size("VIDEO", best_frame_path)

        # 4. 初始化 FaceLandmarker
        print_step("VIDEO", ">> FaceLandmarker 初始化")
        engine = FaceLandmarkerEngine()
        if not engine.is_ready:
            session.error = "FaceLandmarker 未就绪"
            print_error("VIDEO", "FaceLandmarker 初始化失败")
            return None
        print_debug("VIDEO", "FaceLandmarker 就绪")

        # 5. 逐帧处理（降采样到 5fps 等价采样率）
        print_step("VIDEO", f">> 逐帧面部检测 ({len(frames)} 帧)")
        t0 = time.time()
        frame_features = []
        face_detected_count = 0
        for i, frame in enumerate(frames):
            # 前端大约 5fps 传帧，模拟时间戳
            timestamp_ms = int(i * 200)  # 200ms = 5fps
            if i % 30 == 0:
                print_debug("VIDEO", f"面部检测进度: {i+1}/{len(frames)} 帧 (已检测到脸部: {face_detected_count})")

            result = engine.process_frame(frame, timestamp_ms)
            if result.get("face_detected"):
                face_detected_count += 1
            frame_features.append(result)

        face_ratio = face_detected_count / len(frames) * 100 if frames else 0
        print_debug("VIDEO", f"面部检测完成，耗时 {time.time()-t0:.1f}s")
        print_debug("VIDEO", f"面部检测率: {face_detected_count}/{len(frames)} ({face_ratio:.0f}%)")

        # 6. 情绪提取
        print_step("VIDEO", ">> 情绪指标提取")
        t0 = time.time()
        signals = extract_emotion_signals(frame_features)
        print_debug("VIDEO", f"情绪提取完成，耗时 {time.time()-t0:.2f}s")
        print_data("VIDEO", "情绪信号", signals)

        # 7. 构造 EmotionReport
        report = EmotionReport(
            tension_index=signals.get("tension_index", 0.0),
            smile_index=signals.get("smile_index", 0.0),
            overall_emotion=signals.get("overall_emotion", "neutral"),
            gaze_at_camera_pct=signals.get("gaze_at_camera_pct", 0.0),
            head_stability_score=signals.get("head_stability_score", 0.0),
            summary=signals.get("summary", ""),
        ).model_dump()

        session.emotion_report = report
        print_step("VIDEO", f"=== 视频管线完成，总耗时 {time.time()-t_pipeline:.1f}s ===")
        print_data("VIDEO", "emotion_report", report)
        return report

    except ImportError as e:
        session.error = f"视频管线模块缺失: {e}"
        print_error("VIDEO", f"模块缺失: {e}")
        return None
    except Exception as e:
        session.error = f"视频分析异常: {e}"
        print_error("VIDEO", f"异常: {e}")
        logger.exception("视频分析异常")
        return None
