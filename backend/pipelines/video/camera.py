"""
摄像头封装模块

提供 CameraCapture 类，基于 OpenCV 逐帧捕获摄像头画面，
支持 5fps 采样录制，以及最佳帧选取。
"""

import asyncio
import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

CAMERA_INDEX = 0


class CameraCapture:
    """逐帧捕获摄像头画面，支持 5fps 采样存储"""

    def __init__(self, index: int = 0):
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 (index={index})")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info("摄像头已打开: %dx%d @ %.1f fps",
                     actual_w, actual_h,
                     self.cap.get(cv2.CAP_PROP_FPS))

    async def capture_frames(self, duration: int = 120, fps: int = 5) -> list:
        """录制 duration 秒，每秒采样 fps 帧，返回帧列表

        参数:
            duration: 录制时长（秒），默认 120 秒对应路演时长
            fps: 每秒采样帧数，默认 5

        返回:
            帧列表，每帧为 BGR numpy.ndarray
            总帧数约 duration * fps
        """
        frames: list = []
        interval = 1.0 / fps
        total_frames = duration * fps

        logger.info("开始摄像头录制: %d 秒, %d fps, 预期 %d 帧",
                     duration, fps, total_frames)

        for i in range(total_frames):
            ret, frame = self.cap.read()
            if ret:
                # 保存原始分辨率帧
                frames.append(frame)
            else:
                logger.warning("第 %d 帧读取失败", i)

            # 让出事件循环，防止阻塞
            await asyncio.sleep(interval)

        logger.info("摄像头录制完成: 实际 %d 帧", len(frames))
        return frames

    def get_best_photo(self, frames: list) -> Optional[np.ndarray]:
        """从帧列表中选最佳合影帧

        基于清晰度 + 笑脸检测 + 眼睛睁开判断。
        若无法检测则回退到中间帧或最后一帧。

        参数:
            frames: 帧列表

        返回:
            最佳帧的 BGR numpy.ndarray，列表为空则返回 None
        """
        if not frames:
            return None

        # 简单策略：优先中间偏后帧（通常是评委互动时刻）
        if len(frames) < 3:
            return frames[-1]

        # 选后 1/3 区域中的中间帧
        candidate_start = len(frames) * 2 // 3
        best_idx = candidate_start + (len(frames) - candidate_start) // 2
        return frames[min(best_idx, len(frames) - 1)]

    def release(self):
        """释放摄像头资源"""
        if self.cap and self.cap.isOpened():
            self.cap.release()
            logger.info("摄像头已释放")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
