"""
情绪分析模块

从 MediaPipe FaceLandmarker 产出的 blendshapes 序列中提取情绪指标，
包括紧张度、微笑度、看镜头比例、头部稳定性等。
"""

import logging
import math
from typing import Any

import numpy as np

from debug_utils import print_debug, print_step, print_data, print_error

logger = logging.getLogger(__name__)

# 关键 blendshape 名称（ARKit 标准 52 个中选 8 个）
_BROW_INNER_UP = "browInnerUp"
_BROW_OUTER_UP = "browOuterUp"
_JAW_OPEN = "jawOpen"
_MOUTH_PRESS = "mouthPress"
_MOUTH_SMILE_LEFT = "mouthSmileLeft"
_MOUTH_SMILE_RIGHT = "mouthSmileRight"
_EYE_BLINK_LEFT = "eyeBlinkLeft"
_EYE_BLINK_RIGHT = "eyeBlinkRight"

# 紧张度计算权重
_TENSION_WEIGHTS = {
    _BROW_INNER_UP: 0.25,
    _BROW_OUTER_UP: 0.15,
    _JAW_OPEN: 0.20,
    _MOUTH_PRESS: 0.15,
    "blink_rate": 0.25,
}

# 看镜头判定角度阈值（度）
_GAZE_YAW_THRESHOLD = 30.0
_GAZE_PITCH_THRESHOLD = 20.0


def extract_emotion_signals(frame_features: list[dict]) -> dict[str, Any]:
    """从整段路演的所有帧 blendshapes 提取情绪信号

    参数:
        frame_features: 每帧的 dict 列表，包含:
            - blendshapes: [{"category_name": str, "score": float}, ...] 或 None
            - head_pose: {"yaw": float, "pitch": float, "roll": float} 或 None
            - face_detected: bool

    返回:
        {
            "tension_index": float,         # 0-1
            "smile_index": float,           # 0-1
            "overall_emotion": str,         # relaxed_confident | slightly_nervous | tense | neutral
            "gaze_at_camera_pct": float,    # 0-100
            "head_stability_score": float,  # 0-100
            "summary": str,                 # 一句话概述
            "signal_quality": str,          # good | degraded | poor
        }
    """
    # 1. 过滤有效帧
    valid_frames = [f for f in frame_features if f.get("face_detected")]
    total_frames = len(frame_features) if frame_features else 1

    print_step("EMOTION", f"情绪分析: {len(valid_frames)}/{total_frames} 帧检测到人脸")

    if not valid_frames:
        logger.warning("所有帧均未检测到人脸")
        print_error("EMOTION", "所有帧均未检测到人脸")
        return _empty_result("未检测到人脸")

    face_detected_ratio = len(valid_frames) / max(total_frames, 1)
    print_debug("EMOTION", f"人脸检测率: {face_detected_ratio:.0%}")

    # 2. 提取 blendshape 均值
    blendshape_means = _compute_blendshape_means(valid_frames)

    # 3. 计算紧张度
    tension_index = _compute_tension_index(valid_frames, blendshape_means)

    # 4. 计算微笑度
    smile_index = _compute_smile_index(blendshape_means)

    # 5. 计算看镜头率
    gaze_pct = _compute_gaze_percentage(valid_frames)

    # 6. 计算头部稳定度
    head_stability = _compute_head_stability(valid_frames)

    # 7. 判定综合情绪
    overall_emotion = _classify_emotion(tension_index, smile_index)

    # 8. 信号质量
    signal_quality = _classify_signal_quality(face_detected_ratio)

    # 9. 生成概述
    summary = _generate_summary(
        overall_emotion, gaze_pct, head_stability, signal_quality,
    )

    return {
        "tension_index": round(tension_index, 4),
        "smile_index": round(smile_index, 4),
        "overall_emotion": overall_emotion,
        "gaze_at_camera_pct": round(gaze_pct, 1),
        "head_stability_score": round(head_stability, 1),
        "summary": summary,
        "signal_quality": signal_quality,
    }


def _compute_blendshape_means(valid_frames: list[dict]) -> dict[str, float]:
    """计算所有有效帧中各 blendshape 的均值"""
    accum: dict[str, list[float]] = {}
    format_logged = False
    for frame in valid_frames:
        bs_list = frame.get("blendshapes")
        if not bs_list:
            continue
        for bs in bs_list:
            # 兼容 MediaPipe 对象 (.category_name) 和 dict 格式 (get)
            is_obj = hasattr(bs, "category_name")
            if not format_logged:
                print_debug("EMOTION", f"blendshape 格式: {'MediaPipe 对象' if is_obj else 'dict'}")
                format_logged = True
            name = bs.category_name if is_obj else bs.get("category_name", "")
            score = bs.score if is_obj else bs.get("score", 0.0)
            accum.setdefault(name, []).append(score)

    return {name: float(np.mean(scores)) for name, scores in accum.items()}


def _compute_tension_index(
    valid_frames: list[dict],
    means: dict[str, float],
) -> float:
    """综合紧张度计算

    权重分布:
        browInnerUp: 0.25  — 眉头内提（紧张）
        browOuterUp: 0.15  — 眉头外提（紧张）
        jawOpen: 0.20      — 嘴巴微张（紧张）
        mouthPress: 0.15   — 嘴唇紧抿（紧张）
        blink_rate: 0.25   — 眨眼频率（紧张）
    """
    brow_inner = means.get(_BROW_INNER_UP, 0.0)
    brow_outer = means.get(_BROW_OUTER_UP, 0.0)
    jaw_open = means.get(_JAW_OPEN, 0.0)
    mouth_press = means.get(_MOUTH_PRESS, 0.0)

    blink_rate_val = calc_blink_rate(
        [f.get("blendshapes") for f in valid_frames],
    )

    tension = (
        brow_inner * _TENSION_WEIGHTS[_BROW_INNER_UP]
        + brow_outer * _TENSION_WEIGHTS[_BROW_OUTER_UP]
        + jaw_open * _TENSION_WEIGHTS[_JAW_OPEN]
        + mouth_press * _TENSION_WEIGHTS[_MOUTH_PRESS]
        + blink_rate_val * _TENSION_WEIGHTS["blink_rate"]
    )

    return max(0.0, min(1.0, tension))


def _compute_smile_index(means: dict[str, float]) -> float:
    """综合微笑度：左右嘴角上扬幅度的平均值"""
    left = means.get(_MOUTH_SMILE_LEFT, 0.0)
    right = means.get(_MOUTH_SMILE_RIGHT, 0.0)
    smile = (left + right) / 2.0
    return max(0.0, min(1.0, smile))


def _compute_gaze_percentage(valid_frames: list[dict]) -> float:
    """计算看镜头百分比

    基于 head_pose 的 yaw/pitch 判断：
        abs(yaw) < 30 度 and abs(pitch) < 20 度 = 看镜头
    """
    if not valid_frames:
        return 0.0

    looking_count = 0
    for frame in valid_frames:
        pose = frame.get("head_pose")
        if pose is None:
            continue
        yaw = abs(pose.get("yaw", 0))
        pitch = abs(pose.get("pitch", 0))
        if yaw < _GAZE_YAW_THRESHOLD and pitch < _GAZE_PITCH_THRESHOLD:
            looking_count += 1

    return (looking_count / len(valid_frames)) * 100.0


def _compute_head_stability(valid_frames: list[dict]) -> float:
    """计算头部稳定度（0-100）

    综合 yaw（左右转头）、pitch（点头）、roll（歪头）三个轴的抖动：
    取三轴标准差的均方根，分数 = 100 - 合并抖动 * 2。
    头部晃动越大，分数越低。

    注意：旧实现只用 yaw 一个轴，导致点头/歪头/移动时仍判"平稳"。
    """
    yaw_values: list[float] = []
    pitch_values: list[float] = []
    roll_values: list[float] = []
    for frame in valid_frames:
        pose = frame.get("head_pose")
        if pose is not None:
            yaw_values.append(pose.get("yaw", 0.0))
            pitch_values.append(pose.get("pitch", 0.0))
            roll_values.append(pose.get("roll", 0.0))

    if len(yaw_values) < 2:
        return 100.0

    yaw_std = float(np.std(yaw_values))
    pitch_std = float(np.std(pitch_values))
    roll_std = float(np.std(roll_values))
    # 三轴标准差的均方根，综合反映任意方向的头部晃动
    combined_std = (yaw_std ** 2 + pitch_std ** 2 + roll_std ** 2) ** 0.5
    score = 100.0 - combined_std * 2.0
    return max(0.0, min(100.0, score))


def calc_blink_rate(
    blendshapes_list: list,
) -> float:
    """计算眨眼频率指标（0-1）

    基于 eyeBlinkLeft / eyeBlinkRight 两列的均值。
    眨眼频率越高 → 紧张度越高。
    返回 0-1 之间的归一化值。
    """
    blink_scores: list[float] = []
    for bs_list in blendshapes_list:
        if not bs_list:
            continue
        left = 0.0
        right = 0.0
        for bs in bs_list:
            name = bs.category_name if hasattr(bs, "category_name") else bs.get("category_name", "")
            if name == _EYE_BLINK_LEFT:
                left = bs.score if hasattr(bs, "score") else bs.get("score", 0.0)
            elif name == _EYE_BLINK_RIGHT:
                right = bs.score if hasattr(bs, "score") else bs.get("score", 0.0)
        blink_scores.append((left + right) / 2.0)

    if not blink_scores:
        return 0.0

    # 平均眨眼幅度（越高 = 越紧张）
    mean_blink = float(np.mean(blink_scores))

    # 将平均眨眼幅度映射到 0-1 区间
    # 正常眨眼幅度约 0.2-0.4，过度眨眼 > 0.6
    return max(0.0, min(1.0, mean_blink))


def _classify_emotion(tension: float, smile: float) -> str:
    """综合判定情绪类型"""
    if smile > 0.4 and tension < 0.3:
        return "relaxed_confident"
    elif tension > 0.6:
        return "tense"
    elif tension > 0.3 and smile < 0.3:
        return "slightly_nervous"
    else:
        return "neutral"


def _classify_signal_quality(face_detected_ratio: float) -> str:
    """信号质量分级"""
    if face_detected_ratio >= 0.8:
        return "good"
    elif face_detected_ratio >= 0.5:
        return "degraded"
    else:
        return "poor"


def _generate_summary(
    emotion: str,
    gaze_pct: float,
    stability: float,
    signal_quality: str,
) -> str:
    """从指标生成一句话概述"""
    parts = []

    # 情绪描述
    emotion_labels = {
        "relaxed_confident": "整体表现自信放松",
        "slightly_nervous": "整体略微紧张",
        "tense": "整体明显紧张",
        "neutral": "情绪平稳",
    }
    parts.append(emotion_labels.get(emotion, "情绪状态正常"))

    # 看镜头比例
    if gaze_pct >= 80:
        parts.append("看镜头比例较高")
    elif gaze_pct >= 50:
        parts.append(f"看镜头比例约{gaze_pct:.0f}%")
    else:
        parts.append("看镜头较少")

    # 头部稳定度
    if stability < 40:
        parts.append("头部晃动较多")
    elif stability < 70:
        parts.append("头部稳定性一般")

    # 信号质量备注
    if signal_quality == "degraded":
        parts.append("部分时段未检测到人脸")
    elif signal_quality == "poor":
        parts.append("面部信号较差")

    return "，".join(parts) if parts else "情绪分析完成"


def _empty_result(reason: str) -> dict:
    """返回空结果（检测失败时使用）"""
    return {
        "tension_index": 0.0,
        "smile_index": 0.0,
        "overall_emotion": "neutral",
        "gaze_at_camera_pct": 0.0,
        "head_stability_score": 0.0,
        "summary": f"情绪分析失败: {reason}",
        "signal_quality": "poor",
    }
