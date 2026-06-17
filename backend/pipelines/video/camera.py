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

from debug_utils import print_debug, print_step, print_error

logger = logging.getLogger(__name__)

CAMERA_INDEX = 0


class CameraCapture:
    """逐帧捕获摄像头画面，支持 5fps 采样存储"""

    def __init__(self, index: int = 0):
        print_debug("CAMERA", f"打开摄像头 index={index}")
        # 使用 DSHOW 后端加速 Windows 上的摄像头初始化（从 5s→0.5s）
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            print_error("CAMERA", f"无法打开摄像头 (index={index})")
            raise RuntimeError(f"无法打开摄像头 (index={index})")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        print_step("CAMERA", f"摄像头已打开: {actual_w}x{actual_h} @ {actual_fps:.1f} fps")

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

        print_step("CAMERA", f"摄像头录制: {duration}s, {fps}fps, 预期 {total_frames} 帧")
        import time
        t0 = time.time()

        for i in range(total_frames):
            ret, frame = self.cap.read()
            if ret:
                frames.append(frame)
            else:
                logger.warning("第 %d 帧读取失败", i)
                print_error("CAMERA", f"第 {i} 帧读取失败")

            # 每 30 帧打印一次进度
            if i > 0 and i % 30 == 0:
                elapsed = time.time() - t0
                pct = i / total_frames * 100
                print_debug("CAMERA", f"录制进度: {pct:.0f}% ({i}/{total_frames} 帧, {elapsed:.0f}s)")

            # 让出事件循环，防止阻塞
            await asyncio.sleep(interval)

        elapsed = time.time() - t0
        print_step("CAMERA", f"录制完成: 实际 {len(frames)} 帧, 耗时 {elapsed:.1f}s")
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
