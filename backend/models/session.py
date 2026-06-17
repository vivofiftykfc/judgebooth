from dataclasses import dataclass, field
from typing import Any


@dataclass
class BoothSession:
    """评审亭一次会话的状态"""
    step: str = "welcome"          # welcome | presenting | thinking | reviewing | photo | complete
    countdown: int = 0
    audio_path: str | None = None
    transcript: str | None = None
    fluency_report: dict | None = None
    emotion_report: dict | None = None
    review: dict | None = None
    photo_path: str | None = None
    qr_path: str | None = None
    error: str | None = None

    def to_sse(self) -> dict:
        return {
            "step": self.step,
            "countdown": self.countdown,
            "data": {
                "transcript": self.transcript,
                "fluency": self.fluency_report,
                "emotion": self.emotion_report,
                "review": self.review,
                "photo": self.photo_path,
                "qr": self.qr_path,
                "error": self.error,
            },
        }
