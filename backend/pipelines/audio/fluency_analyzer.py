"""
流畅度分析模块

从 Whisper 转写结果中的 segments 列表计算各类演讲流畅度指标。
所有计算基于字符串和正则匹配，不需任何 ML 模型。

典型用法:
    report = analyze_fluency(whisper_result["segments"])
"""

import re
import math
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# 口头禅正则 (Filler words)
# ---------------------------------------------------------------------------
FILLER_PATTERNS: List[re.Pattern] = [
    re.compile(r"嗯[嗯]*"),
    re.compile(r"呃[呃]*"),
    re.compile(r"啊[啊]*"),
    re.compile(r"就是说"),
    re.compile(r"然后"),
    re.compile(r"那个"),
    re.compile(r"这个"),
    re.compile(r"反正"),
    re.compile(r"基本上"),
    re.compile(r"我觉得"),
    re.compile(r"可能\b"),
    re.compile(r"大概"),
]

# ---------------------------------------------------------------------------
# 磕巴检测正则 (Stutters)
# ---------------------------------------------------------------------------
STUTTER_PATTERNS: List[re.Pattern] = [
    re.compile(r"(\S)\1{2,}"),      # 同一个字连续3次以上（我我我）
    re.compile(r"(\w{2,})\1{1,}"),  # 同一个词连续2次以上（就是就是）
]

# ---------------------------------------------------------------------------
# 句子结束标点 — 用于计算有效字数时判断边界
# ---------------------------------------------------------------------------
SENTENCE_END = set("。！？.!?\n")

# ---------------------------------------------------------------------------
# 流畅度综合评分权重 (IMPLEMENTATION.md §3.3.3)
# ---------------------------------------------------------------------------
PAUSE_PENALTY_PER_PAUSE = 1.5
PAUSE_PENALTY_CAP = 15
FILLER_PENALTY_PER_WORD = 2
FILLER_PENALTY_CAP = 15


def analyze_fluency(segments: List[Dict]) -> dict:
    """
    从 Whisper segments 计算全部流畅度指标。

    输入格式:
        [
            {"text": "我们这个项目是", "start": 0.5, "end": 1.2, "confidence": 0.95},
            {"text": "基于深度学习的",  "start": 1.5, "end": 2.8, "confidence": 0.92},
            ...
        ]

    返回:
        dict 包含以下字段（与 FluencyReport 一致）:
            avg_wpm: float             平均语速（字/分钟）
            pause_count: int           停顿次数（>1.5s 间隔）
            longest_pause_seconds: float  最长停顿秒数
            filler_word_count: int     口头禅出现总次数
            filler_examples: list[str] 出现过的口头禅类型（去重）
            stutter_count: int         磕巴事件数
            wpm_volatility: float      语速波动率（10s 窗口 WPM 标准差）
            summary: str               自然语言概述
            score: int                 流畅度综合评分 0-100

    空输入 / 单一段落:
        若 segments 长度 < 2，pause_count 与 longest_pause_seconds 为零，
        其余指标正常计算。若 segments 为空，返回全零报告。
    """
    if not segments:
        return _empty_report()

    # 合并全文
    full_text = "".join(seg["text"] for seg in segments)

    # ---- 语速 (WPM) ------------------------------------------------
    total_chars = _count_chars(full_text)
    total_audio_duration = segments[-1]["end"] - segments[0]["start"]
    total_pause = _calc_total_pause(segments)
    effective_duration = max(total_audio_duration - total_pause, 0.001)  # 避免除以零

    avg_wpm = round(total_chars / effective_duration * 60, 1)

    # ---- 停顿分析 ---------------------------------------------------
    pause_count, pauses = _find_pauses(segments, threshold=1.5)
    longest_pause_seconds = round(max(pauses, default=0.0), 2)

    # ---- 口头禅 -----------------------------------------------------
    filler_count, filler_examples = count_filler_words(full_text)

    # ---- 磕巴 -------------------------------------------------------
    stutter_count = count_stutters(full_text)

    # ---- 语速波动率 ---------------------------------------------------
    wpm_volatility = calc_wpm_per_window(segments, window_s=10.0)

    # ---- 综合评分 ----------------------------------------------------
    score = _calc_fluency_score({
        "avg_wpm": avg_wpm,
        "pause_count": pause_count,
        "filler_word_count": filler_count,
        "wpm_volatility": wpm_volatility,
        "stutter_count": stutter_count,
    })

    # ---- 自然语言概述 ------------------------------------------------
    summary = _generate_summary({
        "avg_wpm": avg_wpm,
        "pause_count": pause_count,
        "longest_pause_seconds": longest_pause_seconds,
        "filler_word_count": filler_count,
        "filler_examples": filler_examples,
        "stutter_count": stutter_count,
    })

    return {
        "avg_wpm": avg_wpm,
        "pause_count": pause_count,
        "longest_pause_seconds": longest_pause_seconds,
        "filler_word_count": filler_count,
        "filler_examples": filler_examples,
        "stutter_count": stutter_count,
        "wpm_volatility": round(wpm_volatility, 1),
        "summary": summary,
        "score": score,
    }


def calc_wpm_per_window(segments: List[Dict], window_s: float = 10.0) -> float:
    """
    计算每 window_s 秒窗口内的 WPM 标准差，用于体现语速波动。

    算法:
        1. 将 segments 按 window_s 对齐的时间窗口分组
        2. 计算每窗口内字数 / 窗口实际非暂停时长 * 60
        3. 返回标准差（窗口数 < 2 时返回 0）

    返回:
        语速波动率（标准差）
    """
    if len(segments) < 2:
        return 0.0

    start_time = segments[0]["start"]
    end_time = segments[-1]["end"]
    total_duration = max(end_time - start_time, 0.001)

    # 确定窗口数
    num_windows = max(int(total_duration / window_s), 1)
    window_bounds = [start_time + i * window_s for i in range(num_windows + 1)]
    if window_bounds[-1] < end_time:
        window_bounds.append(end_time)

    # 将 segment 分配到窗口
    window_wpms = []
    for i in range(len(window_bounds) - 1):
        w_start = window_bounds[i]
        w_end = window_bounds[i + 1]
        segs_in_window = [
            seg for seg in segments
            if seg["start"] < w_end and seg["end"] > w_start
        ]

        if not segs_in_window:
            continue

        # 此窗口内总字符数
        chars = sum(_count_chars(seg["text"]) for seg in segs_in_window)

        # 窗口内有效说话时间 = 窗口大小 - 窗口内暂停总长
        window_total = w_end - w_start
        window_pause = _calc_pause_in_range(segs_in_window, w_start, w_end)
        window_effective = max(window_total - window_pause, 0.001)

        wpm = chars / window_effective * 60
        window_wpms.append(wpm)

    if len(window_wpms) < 2:
        return 0.0

    mean_wpm = sum(window_wpms) / len(window_wpms)
    variance = sum((w - mean_wpm) ** 2 for w in window_wpms) / len(window_wpms)
    return math.sqrt(variance)


def count_filler_words(text: str) -> Tuple[int, List[str]]:
    """
    统计文本中口头禅的出现情况。

    返回:
        (总口头禅数, 出现过的口头禅类型列表（去重）)
    """
    total = 0
    found_types = set()

    for pattern in FILLER_PATTERNS:
        matches = pattern.findall(text)
        count = len(matches)
        if count > 0:
            total += count
            found_types.add(matches[0])

    return total, sorted(found_types)


def count_stutters(text: str) -> int:
    """
    检测文本中磕巴事件数（连续重复的字或词）。

    返回:
        磕巴事件计数
    """
    total = 0
    seen_spans = set()

    for pattern in STUTTER_PATTERNS:
        for match in pattern.finditer(text):
            # 用 match 的起止位置去重，避免同一段文字被两个模式重复计数
            span = match.span()
            if span not in seen_spans:
                seen_spans.add(span)
                total += 1

    return total


# ======================================================================
# 内部辅助函数
# ======================================================================


def _count_chars(text: str) -> int:
    """
    计算文本"有效字数"。

    规则:
        - 中文字符每个计 1 字
        - 连续英文/数字计 1 词（按空格拆分）
        - 标点、空格不计数
    """
    if not text:
        return 0

    # 中文字符
    chinese_chars = len(re.findall(r"[一-鿿]", text))

    # 英文/数字词（连续字母或数字视为一个词）
    english_words = len(re.findall(r"[a-zA-Z0-9]+", text))

    return chinese_chars + english_words


def _calc_total_pause(segments: List[Dict]) -> float:
    """
    计算所有相邻 segment 之间停顿的总时长（仅计 > 1.5s 的间隔）。
    """
    if len(segments) < 2:
        return 0.0

    total = 0.0
    for i in range(1, len(segments)):
        gap = segments[i]["start"] - segments[i - 1]["end"]
        if gap > 1.5:
            total += gap
    return total


def _calc_pause_in_range(segments: List[Dict], range_start: float, range_end: float) -> float:
    """
    计算某时间窗口内所有相邻 segment 间隔中 > 1.5s 的部分，
    且只计算落在窗口内的那部分间隔。
    """
    if len(segments) < 2:
        return 0.0

    total = 0.0
    for i in range(1, len(segments)):
        gap_start = segments[i - 1]["end"]
        gap_end = segments[i]["start"]

        # 间隔与窗口求交集
        overlap_start = max(gap_start, range_start)
        overlap_end = min(gap_end, range_end)
        overlap = overlap_end - overlap_start

        if overlap > 1.5:
            total += overlap
    return total


def _find_pauses(segments: List[Dict], threshold: float = 1.5) -> Tuple[int, List[float]]:
    """
    找出所有超过 threshold 秒的句间隔。

    返回:
        (停顿次数, 每次停顿的秒数列表)
    """
    if len(segments) < 2:
        return 0, []

    pauses = []
    for i in range(1, len(segments)):
        gap = segments[i]["start"] - segments[i - 1]["end"]
        if gap > threshold:
            pauses.append(gap)

    return len(pauses), pauses


def _calc_fluency_score(metrics: dict) -> int:
    """
    依据 IMPLEMENTATION.md §3.3.3 的权重公式计算流畅度综合评分。

    权重:
        - 语速正常度:  20% (是否在 120-200 WPM)
        - 停顿频率:    25% (过多停顿降分)
        - 口头禅密度:  25% (过多降分)
        - 语速波动:    20% (波动大降分)
        - 磕巴:        10% (有则降分)
    """
    score = 100

    # 语速惩罚 (最多 -20)
    wpm = metrics["avg_wpm"]
    if wpm < 80:
        score -= 20
    elif wpm < 120:
        score -= 10
    elif wpm > 250:
        score -= 15
    elif wpm > 200:
        score -= 5

    # 停顿惩罚 (每 1.5 分, 上限 -15)
    pause_penalty = min(metrics["pause_count"] * PAUSE_PENALTY_PER_PAUSE, PAUSE_PENALTY_CAP)
    score -= pause_penalty

    # 口头禅惩罚 (每词 2 分, 上限 -15)
    filler_penalty = min(metrics["filler_word_count"] * FILLER_PENALTY_PER_WORD, FILLER_PENALTY_CAP)
    score -= filler_penalty

    # 波动惩罚
    volatility = metrics["wpm_volatility"]
    if volatility > 40:
        score -= 15
    elif volatility > 25:
        score -= 8

    # 磕巴惩罚 (每次 5 分)
    score -= metrics["stutter_count"] * 5

    return max(int(score), 0)


def _generate_summary(metrics: dict) -> str:
    """
    将流畅度指标转换为自然语言概述（模板驱动）。

    概述模板来源: IMPLEMENTATION.md §5.3
    """
    parts = []

    wpm = metrics["avg_wpm"]
    if wpm < 100:
        parts.append(f"语速偏慢（{wpm}词/分钟），可能不太熟练")
    elif wpm < 140:
        parts.append(f"语速适中偏慢（{wpm}词/分钟）")
    elif wpm < 200:
        parts.append(f"语速适中（{wpm}词/分钟）")
    else:
        parts.append(f"语速偏快（{wpm}词/分钟），可能有点紧张")

    if metrics["pause_count"] > 10:
        parts.append(
            f"出现了{metrics['pause_count']}次停顿，"
            f"最长{metrics['longest_pause_seconds']}秒"
        )

    if metrics["filler_word_count"] > 5:
        examples = "、".join(metrics["filler_examples"])
        parts.append(
            f"使用了{metrics['filler_word_count']}次口头禅（如\"{examples}\"）"
        )

    if metrics["stutter_count"] > 0:
        parts.append(f"有{metrics['stutter_count']}次磕巴")

    return "。".join(parts) + "。"


def _empty_report() -> dict:
    """返回全零的流畅度报告（用于空输入降级）。"""
    return {
        "avg_wpm": 0.0,
        "pause_count": 0,
        "longest_pause_seconds": 0.0,
        "filler_word_count": 0,
        "filler_examples": [],
        "stutter_count": 0,
        "wpm_volatility": 0.0,
        "summary": "未能获取到有效的语音转写内容。",
        "score": 0,
    }
