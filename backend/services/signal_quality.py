def assess_video_quality(frame_count: int, face_detected_count: int) -> str:
    """Evaluate video signal quality based on face detection ratio.

    Returns one of ``"good"``, ``"degraded"``, or ``"poor"``.
    """
    ratio = face_detected_count / max(frame_count, 1)
    if ratio > 0.85:
        return "good"
    if ratio > 0.50:
        return "degraded"
    return "poor"


def assess_audio_quality(whisper_confidence: float) -> str:
    """Evaluate audio signal quality based on Whisper transcription confidence.

    Returns ``"good"`` or ``"degraded"``.
    """
    if whisper_confidence > 0.6:
        return "good"
    return "degraded"
