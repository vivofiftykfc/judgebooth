# 传奇评审亭 — 项目上下文

## 一句话
AI 马斯克评审亭：站到摄像头前展示黑客松项目，获得马斯克风格的硬核评审报告 + 合影。

## 技术栈
- 后端: Python FastAPI (单进程, 无数据库)
- 前端: React + Vite + TailwindCSS + Zustand
- STT: docker-whisper-live (faster-whisper)
- 视觉: Google MediaPipe FaceLandmarker
- TTS: Edge TTS
- LLM: Claude/GPT API

## 目录结构
```
hks/
├── docker-compose.yml    # whisper-live 服务
├── backend/
│   ├── main.py           # FastAPI 入口 + SSE + 5步状态机
│   ├── config.py         # 配置常量
│   ├── models/           # 数据模型
│   │   ├── session.py    # 会话状态
│   │   ├── review.py     # 评审 Schema
│   │   └── performance.py # 表现分析模型
│   ├── pipelines/
│   │   ├── audio/        # 录音 + Whisper + 流畅度
│   │   ├── video/        # 摄像头 + MediaPipe + 情绪
│   │   ├── llm/          # LLM 调用 + Prompt 组装
│   │   ├── tts/          # Edge TTS
│   │   └── output/       # 合影 + QR + H5
│   └── services/         # 管线调度 + 降级
├── frontend/
│   └── src/
│       ├── pages/        # 5 步流程页面
│       ├── components/   # 倒计时/评审卡片/QR
│       ├── stores/       # Zustand 状态机
│       └── hooks/        # SSE 连接
├── PRD.md
├── IMPLEMENTATION.md
└── IMPLEMENT_PLAN.md
```

## 状态机
welcome → presenting → thinking → reviewing → photo → complete

## SSE 协议
后端推送 /api/state SSE:
- step: string (当前步骤)
- countdown: int (倒计时秒数)
- data: dict (各步骤产生的数据)
