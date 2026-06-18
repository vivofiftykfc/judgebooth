import uuid
from dataclasses import dataclass, field
from typing import Any
import os


def _path_to_url(path: str | None) -> str | None:
    """将本地文件路径转为 /static/ 开头的 URL。"""
    if not path:
        return None
    # 提取 data/ 后面的相对路径
    if "\\data\\" in path:
        rel = path.split("\\data\\", 1)[1]
    elif "/data/" in path:
        rel = path.split("/data/", 1)[1]
    else:
        rel = os.path.basename(path)
    return f"/static/{rel.replace(os.sep, '/')}"


@dataclass
class BoothSession:
    """评审亭一次会话的状态"""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    step: str = "welcome"          # welcome | presenting | thinking | reviewing | photo | complete
    countdown: int = 0
    audio_path: str | None = None
    transcript: str | None = None
    transcript_segments: list | None = None   # 前端 Soniox 词级 token 转成的 segments
    fluency_report: dict | None = None
    emotion_report: dict | None = None
    review: dict | None = None
    photo_path: str | None = None
    qr_path: str | None = None
    error: str | None = None

    # 录制阶段的原始数据（大对象，不序列化到 SSE）
    video_frames: list | None = None         # 从浏览器传来的视频帧
    camera_instance: Any | None = None       # CameraCapture 对象（已废弃，保留兼容）

    def to_sse(self) -> dict:
        return {
            "step": self.step,
            "countdown": self.countdown,
            "data": {
                "transcript": self.transcript,
                "fluency": self.fluency_report,
                "emotion": self.emotion_report,
                "review": self.review,
                "review_audio": _path_to_url(self.review_audio_path),
                "photo": _path_to_url(self.photo_path),
                "qr": _path_to_url(self.qr_path),
                "error": self.error,
            },
        }
