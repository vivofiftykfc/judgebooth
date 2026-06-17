# JudgeBooth — 传奇评审亭

> AI 马斯克评审亭：站到摄像头前展示你的黑客松项目，获得马斯克风格的硬核评审报告 + Polaroid 纪念合影。

---

## 快速开始

### 环境要求
- Python 3.10+, Node.js 18+, Windows（音视频硬件）
- 摄像头 + 麦克风

### 后端

```bash
cd backend
pip install fastapi uvicorn sse_starlette pyaudio faster-whisper edge-tts
pip install mediapipe httpx qrcode[pil] pillow

set LLM_API_KEY=your-deepseek-key
set IMG_GEN_API_KEY=your-wavespeedai-key
set KMP_DUPLICATE_LIB_OK=TRUE
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
# 浏览器 http://localhost:5173
```

### AI 生图需要 ngrok（可选）

```bash
D:\ngrok\ngrok.exe http 8000
set PUBLIC_HOST=https://xxx.ngrok-free.dev
```

---

## 使用流程

| 页面 | 操作 |
|------|------|
| Welcome | 自动连接，10s 倒计时 |
| Presenting | 点 **Start** → 路演（最多 60s）→ **End Early** |
| Thinking | 三管线分析中（自动跳转） |
| Reviewing | 展示马斯克评审卡片 → **Continue** |
| PhotoOutput | Polaroid 合影 + 二维码 + H5 |

---

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端 | Python FastAPI + SSE |
| 前端 | React 18 + Vite + TailwindCSS + Zustand |
| 语音转写 | faster-whisper（本地） |
| 面部检测 | MediaPipe FaceLandmarker（478点+52 blendshapes） |
| LLM 评审 | DeepSeek API |
| TTS | Edge TTS |
| AI 合影 | WaveSpeedAI InfiniteYou 换脸 / Pillow 降级 |

---

## 环境变量

| 变量 | 必须 | 说明 |
|------|------|------|
| `LLM_API_KEY` | ✅ | DeepSeek API Key |
| `IMG_GEN_API_KEY` | ✅ | WaveSpeedAI API Key |
| `PUBLIC_HOST` | ⚠️ | ngrok 地址（AI 生图需要） |
| `KMP_DUPLICATE_LIB_OK` | ⚠️ | Whisper OMP 修复，设为 TRUE |

---

## 项目结构

```
backend/     → Python FastAPI（models/pipelines/services）
frontend/    → React（pages/components/stores/hooks）
patches/     → 队友协作补丁
```

详见 `PROJECT_STRUCTURE.md`
