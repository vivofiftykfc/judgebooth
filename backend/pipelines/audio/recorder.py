"""
麦克风录制模块

使用 pyaudio 从系统默认麦克风采集音频，以 WAV 格式保存到
backend/data/audio/ 目录。

典型用法:
    audio_path = await record_audio(duration=120, sample_rate=16000)
"""

import wave
import asyncio
from datetime import datetime
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parents[2] / "data" / "audio"

_recording_stream = None
_recording_active = False


async def record_audio(duration: int = 120, sample_rate: int = 16000) -> str:
    """
    从默认麦克风录制音频并保存为 WAV 文件。

    参数:
        duration:   录制时长，单位秒，默认 120
        sample_rate: 采样率（Hz），默认 16000

    返回:
        生成的 WAV 文件绝对路径。

    抛出:
        ImportError:  pyaudio 未安装或当前系统没有可用麦克风。
        RuntimeError: 录制过程中发生 I/O 错误。

    逻辑:
        1. 确保 data/audio/ 目录存在
        2. 基于当前时间戳生成文件名 recording_YYYYMMDD_HHMMSS.wav
        3. 打开 pyaudio 流 (paInt16, 单声道, 16kHz)
        4. 循环读取帧直到 duration 秒结束
        5. 用 wave 模块写入 16-bit WAV
        6. 返回文件绝对路径
    """
    global _recording_stream, _recording_active

    try:
        import pyaudio
    except ImportError:
        raise ImportError(
            "pyaudio 未安装。"
            "请运行: pip install pyaudio\n"
            "Windows 用户如果安装失败，请先安装 wheel:\n"
            "  pip install pipwin && pipwin install pyaudio\n"
            "或从 https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio 下载对应版本。"
        )

    # 确保输出目录存在
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = AUDIO_DIR / f"recording_{timestamp}.wav"

    # pyaudio 参数
    chunk = 1024
    channels = 1
    audio_format = pyaudio.paInt16

    p = pyaudio.PyAudio()

    # 检查是否有输入设备
    try:
        default_input = p.get_default_input_device_info()
    except (OSError, IOError):
        p.terminate()
        raise ImportError(
            "未检测到麦克风输入设备。请确认麦克风已正确连接。"
        )

    try:
        stream = p.open(
            format=audio_format,
            channels=channels,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk,
        )
    except OSError as e:
        p.terminate()
        raise ImportError(
            f"无法打开音频输入流: {e}\n"
            "请确认麦克风未被其他程序占用且驱动正常。"
        )

    _recording_stream = stream
    _recording_active = True

    frames = []
    total_frames = int(sample_rate / chunk * duration)

    try:
        for _ in range(total_frames):
            if not _recording_active:
                break
            data = stream.read(chunk, exception_on_overflow=False)
            frames.append(data)
            # 每 10 帧让出一次事件循环，避免阻塞其他协程
            if len(frames) % 10 == 0:
                await asyncio.sleep(0)
    except Exception as e:
        raise RuntimeError(f"录制过程中发生错误: {e}")
    finally:
        # 关闭流
        if stream.is_active():
            stream.stop_stream()
        stream.close()
        p.terminate()
        _recording_stream = None
        _recording_active = False

    # 写入 WAV 文件
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(audio_format))
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))

    return str(file_path.resolve())


async def stop_recording():
    """
    停止正在进行的录制。

    安全地关闭 pyaudio 流，丢弃已采集的音频数据。
    """
    global _recording_stream, _recording_active

    _recording_active = False

    if _recording_stream is not None:
        try:
            if _recording_stream.is_active():
                _recording_stream.stop_stream()
            _recording_stream.close()
        except Exception:
            pass  # 流可能已经被释放
        _recording_stream = None
