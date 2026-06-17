"""
麦克风录制模块

使用 pyaudio 回调模式采集音频，支持外部即时停止。
以 WAV 格式保存到 backend/data/audio/ 目录。
"""

import wave
import asyncio
import threading
from datetime import datetime
from pathlib import Path

from debug_utils import print_debug, print_step, print_error

AUDIO_DIR = Path(__file__).resolve().parents[2] / "data" / "audio"

# 全局状态（回调线程和主协程共享）
_recording_active = False
_recording_frames: list[bytes] = []
_recording_stream = None
_recording_pyaudio = None


def _audio_callback(in_data, frame_count, time_info, status):
    """PyAudio 回调：采集音频数据（在音频线程中调用）"""
    global _recording_frames, _recording_active
    if _recording_active:
        _recording_frames.append(in_data)
    return (None, 0)  # pyaudio.paContinue


async def record_audio(duration: int = 60, sample_rate: int = 16000) -> str:
    """
    从默认麦克风录制音频并保存为 WAV 文件（回调模式，支持即时停止）。

    参数:
        duration:   录制时长，单位秒，默认 60
        sample_rate: 采样率（Hz），默认 16000

    返回:
        生成的 WAV 文件绝对路径。
    """
    global _recording_active, _recording_frames, _recording_stream, _recording_pyaudio

    try:
        import pyaudio
    except ImportError:
        print_error("RECORDER", "pyaudio 未安装")
        raise ImportError("pyaudio 未安装")

    # 重置状态
    _recording_frames = []

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = AUDIO_DIR / f"recording_{timestamp}.wav"
    print_step("RECORDER", f"录音文件: {file_path}")

    chunk = 1024
    channels = 1
    audio_format = pyaudio.paInt16

    p = pyaudio.PyAudio()
    _recording_pyaudio = p
    device_count = p.get_device_count()

    # 列出输入设备
    input_devices = []
    for i in range(device_count):
        try:
            info = p.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                input_devices.append((i, info['name'], info['maxInputChannels']))
        except Exception:
            pass

    # 选第一个输入设备
    device_index = None
    if input_devices:
        device_index = input_devices[0][0]
        print_debug("RECORDER", f"选择输入设备: #{device_index} - {input_devices[0][1]}")
    else:
        p.terminate()
        print_error("RECORDER", "未检测到麦克风")
        raise ImportError("未检测到麦克风输入设备")

    try:
        stream = p.open(
            format=audio_format,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=chunk,
            stream_callback=_audio_callback,  # 回调模式！
        )
    except OSError as e:
        # 回退到默认设备
        print_debug("RECORDER", f"指定设备失败，回退到默认: {e}")
        try:
            stream = p.open(
                format=audio_format,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk,
                stream_callback=_audio_callback,
            )
        except OSError as e2:
            p.terminate()
            print_error("RECORDER", f"无法打开音频输入流: {e2}")
            raise ImportError(f"无法打开音频输入流: {e2}")

    _recording_stream = stream
    _recording_active = True
    stream.start_stream()

    print_debug("RECORDER", f"录音开始（回调模式）: {sample_rate}Hz, {channels}ch, 最长 {duration}s")

    # 等待 duration 秒或 _recording_active 变为 False
    for _ in range(duration * 10):  # 每 100ms 检查一次
        if not _recording_active:
            print_debug("RECORDER", "录音被外部停止")
            break
        await asyncio.sleep(0.1)

    # 保存 sample_width 再 terminate
    sample_width = p.get_sample_size(audio_format)

    # 停止
    _recording_active = False
    if stream.is_active():
        stream.stop_stream()
    stream.close()
    p.terminate()
    _recording_stream = None
    _recording_pyaudio = None

    total_frames = len(_recording_frames)
    print_debug("RECORDER", f"录音结束，共采集 {total_frames} 块")

    # 写入 WAV（用提前保存的 sample_width）
    if _recording_frames:
        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(_recording_frames))
        actual_seconds = total_frames * chunk / sample_rate
        print_debug("RECORDER", f"WAV 已写入: {actual_seconds:.1f}s")
        print_step("RECORDER", f"录音完成: {file_path} ({total_frames} 块)")
    else:
        print_error("RECORDER", "没有录到音频帧")

    return str(file_path.resolve())


async def stop_recording():
    """停止正在进行的录制。"""
    global _recording_active, _recording_stream, _recording_pyaudio

    if not _recording_active:
        return

    print_debug("RECORDER", "外部请求停止录音")
    _recording_active = False  # 回调会停止追加数据

    # 不关 stream——由 record_audio 的循环检测到 _recording_active 后自己关
    # 这样避免并发关闭冲突
