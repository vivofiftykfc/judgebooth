import os

# 调试模式（设为 "0" 关闭详细调试输出）
DEBUG_MODE = os.getenv("DEBUG", "1") == "1"

# LLM API (DeepSeek / OpenAI 兼容格式)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# Edge TTS
EDGE_TTS_VOICE = "zh-CN-YunxiNeural"

# Soniox 实时语音转写（浏览器端流式 + 实时字幕）
SONIOX_API_KEY = os.getenv("SONIOX_API_KEY", "")
SONIOX_TEMP_KEY_URL = "https://api.soniox.com/v1/auth/temporary-api-key"
SONIOX_ENABLED = bool(SONIOX_API_KEY)

# Camera
CAMERA_INDEX = 0

# Audio
AUDIO_SAMPLE_RATE = 16000
AUDIO_DURATION = 60  # seconds（最长录音时长）

# Video
VIDEO_FPS = 5
FRAME_INTERVAL = 1.0 / VIDEO_FPS
PHOTO_RESOLUTION = (3840, 2160)
ANALYSIS_RESOLUTION = (1280, 720)

# AI 生图（合影 Polaroid 卡）
IMG_GEN_API_KEY = os.getenv("IMG_GEN_API_KEY", "")     # WaveSpeedAI API Key
IMG_GEN_API_BASE = os.getenv("IMG_GEN_API_BASE", "https://api.wavespeed.ai/api/v3")
IMG_GEN_MODEL = os.getenv("IMG_GEN_MODEL", "wavespeed-ai/flux-krea-dev-lora")
IMG_GEN_ENABLED = bool(IMG_GEN_API_KEY)                 # 有 Key 才启用
