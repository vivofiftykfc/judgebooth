# 传奇评审亭 — 项目上下文

## 一句话
AI 马斯克评审亭：站到摄像头前展示黑客松项目，获得马斯克风格的硬核评审报告 + 合影。

## 当前状态
第二版调试完成，核心流程已跑通。代码 ~5300 行（后端 3200 + 前端 800 + 文档/配置 1300）。
需要设 `LLM_API_KEY` 和 `IMG_GEN_API_KEY` 环境变量。

## 技术栈
- 后端: Python FastAPI (单进程, 无数据库)
- 前端: React + Vite + TailwindCSS + Zustand + Framer Motion
- STT: faster-whisper (本地, CTranslate2)
- 视觉: Google MediaPipe FaceLandmarker (478 点 + 52 blendshapes)
- TTS: Edge TTS (zh-CN-YunxiNeural)
- LLM: DeepSeek API (OpenAI 兼容格式)
- 生图: WaveSpeedAI InfiniteYou 换脸（Polaroid 模板 + 人脸替换）
- 合影: Pillow 合成 Polaroid 卡 / AI 生图（自动降级）

## 快速启动

```bash
# 终端 1: 后端
cd D:\hks\backend
set LLM_API_KEY=sk-6e863dcd99a94c63a7065c43cadc4cbe
set IMG_GEN_API_KEY=wsk_live_IkQ-6Xb8sNokbMgAzDJ6r9-tcGtWrJtOK3MwmryGgqw
set PUBLIC_HOST=http://localhost:8000
uvicorn main:app --host 0.0.0.0 --port 8000

# 终端 2: 前端
cd D:\hks\frontend && npm run dev
# 浏览器打开 http://localhost:5173

# 终端 3: ngrok（可选，AI 生图需要公网 URL）
D:\ngrok\ngrok.exe http 8000
# 设 PUBLIC_HOST 为 ngrok 地址
```

## 目录结构
```
hks/
├── backend/
│   ├── main.py              # FastAPI + SSE + 5步状态机
│   ├── config.py            # 配置常量
│   ├── debug_utils.py       # 统一调试打印
│   ├── models/
│   │   ├── session.py       # BoothSession 会话状态
│   │   ├── review.py        # 评审报告 Schema
│   │   └── performance.py   # FluencyReport + EmotionReport
│   ├── pipelines/
│   │   ├── audio/           # recorder(回调模式) → faster-whisper → fluency
│   │   ├── video/           # 前端帧 → FaceLandmarker → emotion
│   │   ├── llm/             # prompt_builder → DeepSeek API → review
│   │   ├── tts/             # Edge TTS 合成
│   │   └── output/          # img_gen_engine + photo_composer + qr + h5
│   ├── services/            # pipeline_orchestrator 三管线调度
│   └── assets/              # 素材（polaroid_template.png 等）
├── frontend/
│   └── src/
│       ├── pages/           # Welcome / Presenting(Start按钮) / Thinking / Reviewing / PhotoOutput
│       ├── components/      # Countdown / ReviewCard / QRDisplay
│       ├── stores/          # Zustand boothStore
│       └── hooks/           # useBoothSSE
├── patches/                 # 补丁文件（队友协作用）
├── CLAUDE.md / CHANGELOG.md / PROJECT_STRUCTURE.md / DEBUG_TUTORIAL.md
└── PROMPT_ENGINEERING.md    # 提示词工程指南
```

## 状态机
welcome → presenting → thinking → reviewing → photo → complete

## 核心流程

```
1. Welcome（10s 倒计时）→ 自动跳转 presenting
2. Presenting（点 Start → 录音 60s + 前端发帧 5fps）
3. End Early / 倒计时归零 → 停止录音 → 三管线分析
   ├─ 音频: WAV → Whisper → 流畅度
   ├─ 视频: 前端帧 → FaceLandmarker → 情绪
   └─ LLM: 转写+流畅度+情绪 → DeepSeek → 评审
4. Reviewing（展示 5 段评审卡片）
5. PhotoOutput（Polaroid 合影 + 二维码 + H5 页面）
```

## API 端点
```
POST /api/step/welcome                    → 重置会话
POST /api/step/presenting/start           → 开始录音
POST /api/step/presenting/end             → 停止录音 → 启动三管线
POST /api/step/presenting/frame           → 接收前端视频帧
POST /api/step/thinking/complete          → 进入评审（已废弃，自动推进）
POST /api/step/reviewing/complete         → 完成评审 → 生成合影
POST /api/step/photo/complete             → 完成合影
GET  /api/health                          → 健康检查
GET  /api/stream                          → SSE 实时推送
```

## 关键改动记录（2026-06-18）

### 录音系统
- 从 PyAudio 阻塞模式改为回调模式，支持即时停止
- 录音时长 60s，可 End Early 提前结束
- 录音 → 保存 → 分析管线直接使用已有文件（不重录）

### 摄像头与视频
- 去掉后端 OpenCV 录帧，改为前端 canvas 截图 → Base64 → POST 发帧
- 前端 `getUserMedia` 做摄像头预览

### LLM 评审
- 接入 DeepSeek API（OpenAI 兼容格式）
- 马斯克人设重写（5 思维模型 + 评审铁律 + 对抗性语气）
- 增加 one-shot 示例锚定输出风格
- 空转写/弱项目直接点破

### 合影生成
- AI 生图: WaveSpeedAI InfiniteYou 换脸（模板 + 人脸替换）
- Pillow 降级: 赛博朋克 Polaroid 卡 / 二维码右下角
- 公网 URL 通过 PUBLIC_HOST 环境变量配置

### 调试系统
- 统一调试工具 `debug_utils.py`（[STEP]/[DATA]/[ERROR] 标记）
- 17 个后端文件加入调试输出
- 详尽的 DEBUG_TUTORIAL.md

### 修复的 Bug
- 录音停不下来 / 录两遍 / terminate 后调用 PyAudio
- Thinking 页面卡死（自动推进 reviewing）
- 合影/二维码不显示（Vite proxy + 静态文件挂载）
- End Early 按钮不响应（乐观更新跳过 SSE）
- session_id 不存在导致 QR 崩溃
- H5 页面数据为空（生成时 session 被重置 → 快照机制）

## 环境变量
| 变量 | 必须 | 说明 |
|------|------|------|
| `LLM_API_KEY` | ✅ | DeepSeek API Key |
| `IMG_GEN_API_KEY` | ✅ | WaveSpeedAI API Key（生图/换脸） |
| `PUBLIC_HOST` | ⚠️ AI生图需要 | ngrok 公网地址 |
| `DEBUG` | 否 | 调试输出开关（默认开） |
