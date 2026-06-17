# 传奇评审亭 — 实现执行方案

> **版本**: v1.0
> **日期**: 2026-06-17
> **策略**: 多 Agent 并行实现 + 逐波审查 + 端到端联调

---

## 总体策略

```
文件路径不重叠 = 可以并行
每波完成后 = code-review 审查
审查通过 = 进入下一波
最终 = quality-gate + security-reviewer
```

---

## 波次总览

| Wave | 执行者 | 内容 | 产出文件数 | 耗时 | 并行 |
|------|--------|------|-----------|------|------|
| 0 | **我** | 目录骨架 + Docker + Config | ~5 | 5min | — |
| 1A | Agent A | FastAPI 主应用 + 数据模型 + 状态机 | ~8 | 15min | ✅ 与 1B |
| 1B | Agent B | 音频管线（录音 + Whisper + 流畅度） | ~3 | 15min | ✅ 与 1A |
| 1.5 | **审查** | `code-review` 技能 | — | 5min | — |
| 2C | Agent C | 视频管线（摄像头 + MediaPipe + 情绪） | ~3 | 15min | ✅ 与 2D |
| 2D | Agent D | LLM + TTS + 输出（合影/QR/H5） | ~7 | 20min | ✅ 与 2C |
| 2.5 | **审查** | `code-review` 技能 | — | 5min | — |
| 3 | Agent E | React 前端（5 页面 + SSE + 动画） | ~11 | 20min | 单独 |
| 3.5 | **审查** | `code-review` + `typescript-reviewer` | — | 5min | — |
| 4 | **我** | 端到端联调 + 修复 | — | 20min | — |
| 4.5 | **最终检查** | `quality-gate` + `security-reviewer` | — | 5min | — |
| | **合计** | | **~15 文件，~1350 行** | **~2h** | |

---

## Wave 0：骨架搭建（我直接做）

### 操作清单

| 操作 | 说明 |
|------|------|
| `mkdir -p` 全部目录结构 | 后端 ~15 个目录，前端 ~8 个目录 |
| 写 `docker-compose.yml` | whisper-live 服务 |
| 写 `backend/requirements.txt` | fastapi, uvicorn, mediapipe, opencv-python, pyaudio, edge-tts, httpx, Pillow, qrcode, numpy |
| 写 `frontend/package.json` | Vite + React + TailwindCSS + Framer Motion + Zustand |
| 写 `CLAUDE.md` | 项目上下文，供后续 Agent 读取 |

### 为什么自己做

目录结构一旦定下来就不能变。后续 Agent 写文件时路径必须一致。5 分钟搞定。

### 目录结构

```
hks/
├── docker-compose.yml           # whisper-live 服务
├── CLAUDE.md                    # 项目上下文
├── backend/
│   ├── main.py                  # FastAPI 入口 + 状态机路由
│   ├── config.py                # 全局配置
│   ├── requirements.txt
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py           # 会话数据模型
│   │   ├── review.py            # 评审报告 Schema
│   │   └── performance.py       # 表现分析数据结构
│   ├── pipelines/
│   │   ├── audio/
│   │   │   ├── __init__.py
│   │   │   ├── recorder.py      # 麦克风录制
│   │   │   ├── whisper_engine.py # Whisper 转写
│   │   │   └── fluency_analyzer.py # 流畅度分析
│   │   ├── video/
│   │   │   ├── __init__.py
│   │   │   ├── camera.py        # 摄像头控制
│   │   │   ├── mediapipe_engine.py # MediaPipe FaceLandmarker
│   │   │   └── emotion_analyzer.py # 情绪指标提取
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── llm_engine.py    # LLM API 调用
│   │   │   ├── persona.py       # 女娲.skill 集成
│   │   │   └── prompt_builder.py # Prompt 组装
│   │   ├── tts/
│   │   │   ├── __init__.py
│   │   │   └── tts_engine.py    # Edge TTS
│   │   └── output/
│   │       ├── __init__.py
│   │       ├── photo_composer.py # 合影合成
│   │       ├── qr_generator.py   # 二维码
│   │       └── h5_generator.py   # H5 页面生成
│   └── services/
│       ├── __init__.py
│       ├── pipeline_orchestrator.py # 三管线调度器
│       ├── signal_quality.py    # 信号质量评估
│       └── degradation.py       # 降级策略
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── stores/
│       │   └── boothStore.ts    # Zustand 状态机
│       ├── pages/
│       │   ├── Welcome.tsx      # Step 1
│       │   ├── Presenting.tsx   # Step 2
│       │   ├── Thinking.tsx     # Step 3
│       │   ├── Reviewing.tsx    # Step 4
│       │   └── PhotoOutput.tsx  # Step 5
│       ├── components/
│       │   ├── Countdown.tsx    # 倒计时组件
│       │   ├── ReviewCard.tsx   # 评审卡片
│       │   └── QRDisplay.tsx    # 二维码展示
│       └── hooks/
│           └── useBoothSSE.ts   # SSE 连接
├── PRD.md
├── IMPLEMENTATION.md
└── IMPLEMENT_PLAN.md
```

---

## Wave 1：后端核心（并行 2 Agent）

### Agent A：FastAPI 主应用

**写什么**（文件路径完全不与 Agent B 重叠）：

| 文件 | 内容 |
|------|------|
| `backend/main.py` | FastAPI 入口 + SSE 端点 + 5 步路由 + 启动事件 |
| `backend/config.py` | 所有配置常量（Whisper URL、LLM key、摄像头 index 等） |
| `backend/models/session.py` | 会话数据模型（state, step, countdown, data） |
| `backend/models/review.py` | 评审报告 Schema（5 段结构） |
| `backend/models/performance.py` | 表现分析数据模型（流畅度 + 情绪） |
| `backend/services/pipeline_orchestrator.py` | 三管线调度器（音频→视频→LLM 的执行顺序） |
| `backend/services/signal_quality.py` | 信号质量判定（视频追踪率、音频置信度） |
| `backend/services/degradation.py` | 降级策略（条件→动作映射表） |

**给 Agent 的上下文**：
- PRD.md 中的 5 步流程定义
- IMPLEMENTATION.md 中 SSE 通信格式
- Wave 0 已创建的全部目录结构

**验收标准**：`uvicorn backend.main:app` 能启动，`GET /health` 返回 200

---

### Agent B：音频管线

**写什么**（文件路径完全不与 Agent A 重叠）：

| 文件 | 内容 |
|------|------|
| `pipelines/audio/recorder.py` | pyaudio 录制 120s → 16kHz WAV 文件 + 环形缓冲区 |
| `pipelines/audio/whisper_engine.py` | HTTP 调用 docker-whisper-live 转写 + 重试逻辑 |
| `pipelines/audio/fluency_analyzer.py` | 语速/WPM、停顿计数、口头禅检测、磕巴检测 |

**给 Agent 的上下文**：
- docker-whisper-live 的 REST API 地址 (`localhost:9090`)
- IMPLEMENTATION.md 第 3 节中的流畅度分析算法
- 输出格式必须匹配 `models/performance.py` 中的 `FluencyReport`

**验收标准**：传入一个 WAV 文件，返回带时间戳的转写文本 + 流畅度指标

---

### 为什么能并行

| Agent | 写入路径 | 冲突？ |
|-------|---------|--------|
| A | `main.py`, `config.py`, `models/*.py`, `services/*.py` | — |
| B | `pipelines/audio/*.py` | ❌ 完全不重叠 |

---

## Wave 1.5：审查

```
技能: ecc:code-review
范围: Wave 1 产出的全部文件

检查项：
- SSE 推送格式是否正确（字段名、类型）
- Whisper 调用是否加了超时 + 重试（网络不可靠）
- 数据模型一致性：Agent A 的 PerformanceReport 和 Agent B 的 FluencyReport 字段对齐

问题处理: 如果有问题 → ecc:build-fix 修复 → 再进 Wave 2
```

---

## Wave 2：LLM + 视觉 + 输出（并行 2 Agent）

### Agent C：视频管线

**写什么**（文件路径完全不与 Agent D 重叠）：

| 文件 | 内容 |
|------|------|
| `pipelines/video/camera.py` | OpenCV 摄像头控制（初始化、逐帧读取、调整参数） |
| `pipelines/video/mediapipe_engine.py` | Google FaceLandmarker 新版 API 封装（逐帧推理） |
| `pipelines/video/emotion_analyzer.py` | 从 52 blendshapes 提取 8 个关键信号 + 头部姿态 |

**给 Agent 的上下文**：
- IMPLEMENTATION.md 第 4 节中的 MediaPipe 新版 API 用法
- 8 个关键 blendshape 的选取逻辑
- 输出必须匹配 `models/performance.py` 中的 `EmotionReport`

**验收标准**：给一帧图像，返回 478 个关键点 + 情绪指标（tension/smile/gaze）

---

### Agent D：LLM + TTS + 输出

**写什么**（文件路径完全不与 Agent C 重叠）：

| 文件 | 内容 |
|------|------|
| `pipelines/llm/llm_engine.py` | LLM API 调用（Claude/GPT）+ 超时 + 重试 + 结构化解析 |
| `pipelines/llm/prompt_builder.py` | Prompt 组装（流畅度 + 情绪 → 自然语言段落 → 完整 Prompt） |
| `pipelines/llm/persona.py` | 女娲.skill 集成 / 角色定义 |
| `pipelines/tts/tts_engine.py` | Edge TTS 合成 + 音频缓存 |
| `pipelines/output/photo_composer.py` | 最佳帧选取 + 签名叠加 + Logo + 文字渲染 |
| `pipelines/output/qr_generator.py` | qrcode 库生成二维码 |
| `pipelines/output/h5_generator.py` | 单页 HTML 生成 + 上传逻辑 |

**给 Agent 的上下文**：
- PRD.md 中的 5 段评审结构 + 女娲.skill 接口约定
- IMPLEMENTATION.md 第 5-6 节中的 Prompt 格式
- Edge TTS 的简单用法

**验收标准**：给定转写文本 + 情绪指标，返回完整评审 + 合成音频 + 合影图片

---

### 为什么能并行

| Agent | 写入路径 | 冲突？ |
|-------|---------|--------|
| C | `pipelines/video/*.py` | — |
| D | `pipelines/llm/*.py`, `pipelines/tts/*.py`, `pipelines/output/*.py` | ❌ 完全不重叠 |

---

## Wave 2.5：审查

```
技能: ecc:code-review
范围: Wave 2 产出的全部文件

检查项：
- 情绪分析是否正确处理降级情况（face not found → 跳过）
- LLM 调用是否有超时/重试/降级
- TTS 音频缓存策略
- 合影合成是否处理了帧格式转换
```

---

## Wave 3：前端（单独 1 Agent）

### Agent E：React 前端

**写什么**：

| 文件 | 内容 |
|------|------|
| `frontend/src/App.tsx` | 路由 + 全局状态绑定 |
| `frontend/src/stores/boothStore.ts` | Zustand 状态机（step, countdown, data） |
| `frontend/src/pages/Welcome.tsx` | Step 1：欢迎页 + 人脸检测指示 |
| `frontend/src/pages/Presenting.tsx` | Step 2：120s 倒计时 + 音量波形 |
| `frontend/src/pages/Thinking.tsx` | Step 3：加载动画 |
| `frontend/src/pages/Reviewing.tsx` | Step 4：评审文字逐段同步 + 进度 |
| `frontend/src/pages/PhotoOutput.tsx` | Step 5：合影预览 + 二维码 |
| `frontend/src/components/Countdown.tsx` | 倒计时组件 |
| `frontend/src/components/ReviewCard.tsx` | 评审段落卡片 |
| `frontend/src/components/QRDisplay.tsx` | 二维码展示 |
| `frontend/src/hooks/useBoothSSE.ts` | SSE 连接 + 自动重连 |

**给 Agent 的上下文**：
- SSE 协议格式（from `main.py` 的端点定义）
- UI 设计参考（PRD.md 中的用户体验旅程）
- 全屏 kiosk 模式要求

**验收标准**：`npm run dev` 能启动，5 个页面可切换

---

## Wave 3.5：审查

```
技能: ecc:code-review + typescript-reviewer
范围: 全部前端文件 + 前后端接口对齐

重点检查：
- SSE 数据字段类型是否正确
- 倒计时逻辑是否精确（setInterval vs requestAnimationFrame）
- 页面切换是否有过渡动画
- 组件 Props 类型定义
```

---

## Wave 4：端到端联调（我亲自做）

### 联调步骤

```
1. docker-compose up -d              # 启动 whisper-live
2. cd backend && uvicorn main:app     # 启动 FastAPI (localhost:8000)
3. cd frontend && npm run dev         # 启动 React (localhost:5173)
4. 打开 http://localhost:5173 全屏
5. 走完 5 步流程
6. 修复发现的问题
```

### 已知高风险项

| 风险 | 原因 | 应对 |
|------|------|------|
| 摄像头 index 不对 | Windows 下 USB 摄像头可能是 1 而非 0 | `config.py` 中加可配置项 |
| 麦克风设备选择 | pyaudio 默认设备可能不是你插的那个 | 加设备列表打印 |
| 音频格式对齐 | whisper-live 期望 16kHz mono | recorder.py 中确保格式转换 |
| SSE 跨域 | 前后端不同端口 | FastAPI 加 CORSMiddleware |
| 中文 TTS 延迟 | Edge TTS 首次请求较慢 | 启动时预热 |

---

## Wave 4.5：最终检查

```
技能: ecc:quality-gate
检查内容:
- 所有文件存在
- 所有 import 可解析
- Python 语法无错误
- TypeScript 无类型错误

技能: security-reviewer
检查内容:
- 无硬编码 API key
- 无文件路径泄露
- 无 unsafe 的 eval/exec
- 无过宽 CORS 配置
```

---

## Agent 提示词策略

每个 Agent 启动时，我会给以下上下文：

```
1. 项目背景（一句话：黑客松评审亭）
2. 你的任务（你要写哪几个文件）
3. 文件路径清单 + 每个文件的职责
4. 你依赖的数据模型（从 models/ 中 import 什么）
5. 你的输出被谁消费（下游模块）
6. 验收标准（怎么算完成）
7. 从哪里读取已有文件（读取 models/ 了解字段定义）
```

示例（Agent C 视频管线）：

```
你是 Agent C，负责视频管线。

你要写 3 个文件：
- pipelines/video/camera.py       → OpenCV 摄像头封装
- pipelines/video/mediapipe_engine.py → MediaPipe FaceLandmarker
- pipelines/video/emotion_analyzer.py → 情绪指标提取

你的输入：摄像头帧（来自 camera.py）
你的输出：EmotionReport（定义在 models/performance.py，请先读这个文件）
你的下游：pipeline_orchestrator.py（由 Agent A 写）

验收：给一帧图像，返回 478 关键点 + 情绪指标
```

---

## 附录：技能速查

| 技能 | 何时用 |
|------|--------|
| `ecc:code-review` | 每波完成后 |
| `ecc:build-fix` | Python/FastAPI 构建失败 |
| `ecc:react-build` | React/前端构建失败 |
| `ecc:quality-gate` | 最终交付前 |
| `security-reviewer` (agent) | 最终安全检查 |
| `typescript-reviewer` (agent) | 前端类型审查 |
