"""
MediaPipe FaceLandmarker 引擎封装

使用 Google MediaPipe 新版 tasks API，
输出 478 个面部关键点 + 52 个 ARKit blendshapes 表情系数。
"""

import logging
import os
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# 模型文件路径（相对此文件所在目录）
MODEL_PATH = os.path.join(os.path.dirname(__file__), "face_landmarker_v2.task")
MODEL_DOWNLOAD_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
)

# 头部姿态估计使用的 5 个稳定关键点索引
# MediaPipe FaceLandmarker 478 点模型中选取：
#   鼻尖, 下巴, 右眼外眼角, 左眼外眼角, 上唇中点
HEAD_POSE_LANDMARK_IDS = [1, 152, 263, 33, 13]

# 对应 3D 模型坐标（从 MediaPipe 规范正面模型采样，单位 mm）
_HEAD_POSE_MODEL_POINTS = np.array([
    [0.0, 0.0, 0.0],        # 鼻尖 (landmark 1)
    [0.0, -330.0, -65.0],   # 下巴 (landmark 152)
    [225.0, 170.0, -135.0], # 右眼外眼角 (landmark 263)
    [-225.0, 170.0, -135.0],# 左眼外眼角 (landmark 33)
    [0.0, -150.0, -135.0],  # 上唇中点 (landmark 13)
], dtype=np.float64)


class FaceLandmarkerEngine:
    """Google FaceLandmarker 封装，输出 478 关键点 + 52 ARKit blendshapes"""

    def __init__(self, model_path: str = MODEL_PATH):
        self._model_path = model_path
        self._detector = None

        if not os.path.isfile(model_path):
            logger.warning(
                "MediaPipe 模型文件未找到: %s\n"
                "请手动下载后放置到该路径:\n%s",
                model_path, MODEL_DOWNLOAD_URL
            )
            # 不崩溃，process_frame 会在检测器为 None 时优雅返回
            return

        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_faces=1,
                output_face_blendshapes=True,
                min_face_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._detector = vision.FaceLandmarker.create_from_options(options)
            logger.info("FaceLandmarker 引擎初始化完成")
        except ImportError:
            logger.warning("mediapipe 库未安装，FaceLandmarker 不可用")
        except Exception as e:
            logger.error("FaceLandmarker 初始化失败: %s", e)

    @property
    def is_ready(self) -> bool:
        """引擎是否可用"""
        return self._detector is not None

    def process_frame(self, frame: np.ndarray, timestamp_ms: int) -> dict:
        """处理一帧，检测面部关键点和表情系数

        参数:
            frame: BGR 格式图像帧
            timestamp_ms: 帧时间戳（毫秒），用于 VIDEO 模式

        返回:
            {
                "face_detected": True/False,
                "landmarks": [[x, y, z], ...] 或 None,  # 478 个点
                "blendshapes": [
                    {"category_name": "browInnerUp", "score": 0.3},
                    ...
                ] 或 None,  # 52 个 ARKit blendshapes
                "head_pose": {"yaw": 0, "pitch": 0, "roll": 0} 或 None,
            }
        """
        result = {
            "face_detected": False,
            "landmarks": None,
            "blendshapes": None,
            "head_pose": None,
        }

        if not self.is_ready:
            logger.debug("FaceLandmarker 未就绪，跳过帧处理")
            return result

        try:
            from mediapipe.framework.formats import landmark_pb2
            from mediapipe.tasks.python.vision.core import vision_task_running_mode

            # 转为 mp.Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = self._to_mp_image(rgb_frame)

            detection_result = self._detector.detect_for_video(mp_image, timestamp_ms)

            if not detection_result.face_landmarks:
                return result

            # 面部检测成功
            result["face_detected"] = True

            # 提取 478 个关键点
            face_landmarks = detection_result.face_landmarks[0]
            result["landmarks"] = [
                [lm.x, lm.y, lm.z] for lm in face_landmarks
            ]

            # 提取 52 个 blendshapes
            if detection_result.face_blendshapes:
                result["blendshapes"] = [
                    {
                        "category_name": bs.category_name,
                        "score": bs.score,
                    }
                    for bs in detection_result.face_blendshapes[0]
                ]

            # 估算头部姿态
            landmarks_array = np.array(result["landmarks"])
            result["head_pose"] = self.estimate_head_pose(landmarks_array)

        except Exception as e:
            logger.error("帧处理异常: %s", e)

        return result

    def estimate_head_pose(self, landmarks: np.ndarray) -> dict:
        """从 478 个关键点估算头部欧拉角

        使用 5 个稳定特征点 + cv2.solvePnP 求解旋转向量，
        转换为 yaw（偏航）、pitch（俯仰）、roll（翻滚）角度。

        参数:
            landmarks: shape (478, 3) 的关键点数组

        返回:
            {"yaw": float, "pitch": float, "roll": float}
            角度单位：度，范围约 [-180, 180]
        """
        # 默认返回值
        default = {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

        if landmarks.shape[0] < max(HEAD_POSE_LANDMARK_IDS) + 1:
            return default

        # 提取 2D 图像点（x, y 像素坐标）
        # 注意 landmarks 中 x, y 是归一化坐标 [0, 1]，需乘以图像尺寸
        # 但 solvePnP 可以用归一化坐标配合适当的相机内参
        # 为简化，假设相机内参为单位矩阵，用归一化坐标求解相对姿态
        image_points = np.array([
            landmarks[i][:2] for i in HEAD_POSE_LANDMARK_IDS
        ], dtype=np.float64)

        # 相机内参（近似，使用归一化坐标的合理假设）
        focal_length = 1.0
        center = (0.5, 0.5)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        try:
            success, rvec, tvec = cv2.solvePnP(
                _HEAD_POSE_MODEL_POINTS,
                image_points,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )

            if not success:
                return default

            # 旋转向量 → 旋转矩阵 → 欧拉角
            rmat, _ = cv2.Rodrigues(rvec)
            return self._rotation_matrix_to_euler(rmat)

        except cv2.error:
            return default

    @staticmethod
    def _rotation_matrix_to_euler(rmat: np.ndarray) -> dict:
        """旋转矩阵转欧拉角（yaw, pitch, roll）"""
        sy = np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
        singular = sy < 1e-6

        if not singular:
            yaw = np.arctan2(rmat[1, 0], rmat[0, 0])
            pitch = np.arctan2(-rmat[2, 0], sy)
            roll = np.arctan2(rmat[2, 1], rmat[2, 2])
        else:
            yaw = np.arctan2(-rmat[1, 2], rmat[1, 1])
            pitch = np.arctan2(-rmat[2, 0], sy)
            roll = 0.0

        return {
            "yaw": float(np.degrees(yaw)),
            "pitch": float(np.degrees(pitch)),
            "roll": float(np.degrees(roll)),
        }

    @staticmethod
    def _to_mp_image(rgb_frame: np.ndarray):
        """将 RGB numpy 数组转为 MediaPipe Image"""
        from mediapipe.image import Image, ImageFormat
        return Image(image_format=ImageFormat.SRGB, data=rgb_frame)
