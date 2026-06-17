import os

# LLM API (DeepSeek / OpenAI 兼容格式)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# Edge TTS
EDGE_TTS_VOICE = "zh-CN-YunxiNeural"

# Camera
CAMERA_INDEX = 0

# Audio
AUDIO_SAMPLE_RATE = 16000
AUDIO_DURATION = 120  # seconds

# Video
VIDEO_FPS = 5
FRAME_INTERVAL = 1.0 / VIDEO_FPS
PHOTO_RESOLUTION = (3840, 2160)
ANALYSIS_RESOLUTION = (1280, 720)
