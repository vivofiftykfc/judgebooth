def decide_emotion_degradation(video_quality: str) -> dict:
    """Determine emotion-analysis degradation behaviour based on video quality.

    Returns a dict with ``enabled`` (bool) and ``note`` (str | None).
    """
    mapping = {
        "good": {"enabled": True, "note": None},
        "degraded": {"enabled": True, "note": "自信度分析受限"},
        "poor": {"enabled": False, "note": "自信度分析未启用（画面质量不足）"},
    }
    return mapping.get(video_quality, mapping["poor"])


def decide_fluency_degradation(audio_quality: str) -> dict:
    """Determine fluency-analysis degradation behaviour based on audio quality.

    Returns a dict with ``enabled`` (bool) and ``note`` (str | None).
    """
    mapping = {
        "good": {"enabled": True, "note": None},
        "degraded": {"enabled": True, "note": "流畅度分析仅供参考（音频质量不佳）"},
    }
    return mapping.get(audio_quality, mapping["degraded"])
