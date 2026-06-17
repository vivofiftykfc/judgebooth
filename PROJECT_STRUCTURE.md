# 项目结构总览

```
hks/
├── backend/              ← Python FastAPI 后端
├── frontend/             ← React + Vite 前端
├── hackathon/            ← 旧版备份（可忽略）
├── .claude/              ← Claude 配置
├── .git/                 ← Git 仓库
│
├── CLAUDE.md             ← 项目上下文（给 AI 看的）
├── PRD.md                ← 产品需求文档
├── IMPLEMENTATION.md     ← 技术实现方案
├── IMPLEMENT_PLAN.md     ← 多 Agent 执行计划
├── DEBUG_PLAN.md         ← 三人分工调试手册
├── MAIN_DEBUG.md         ← 主干调试操作手册
├── DEBUG_TUTORIAL.md     ← 保姆级调试教程
├── PROJECT_STRUCTURE.md  ← 本文件
├── SESSION_SUMMARY.md    ← 开发过程记录
├── docker-compose.yml    ← （废弃，已改用本地 faster-whisper）
└── .gitignore
```

---

## backend/ — 后端（Python FastAPI）

```
backend/
├── main.py               ← HTTP 入口 + SSE 推送 + 5 步状态机
├── config.py             ← 配置常量（API Key、时长、摄像头索引）
├── debug_utils.py        ← 统一调试打印工具
├── requirements.txt      ← Python 依赖
│
├── models/               ← 数据模型
│   ├── session.py        ← BoothSession 会话状态（含 to_sse()）
│   ├── review.py         ← ReviewReport 评审报告结构
│   └── performance.py    ← FluencyReport + EmotionReport
│
├── pipelines/            ← 5 条数据处理管线
│   ├── audio/            ← 音频管线
│   │   ├── recorder.py         ← PyAudio 录音（回调模式，支持即时停止）
│   │   ├── whisper_engine.js   ← faster-whisper 语音转写
│   │   ├── fluency_analyzer.py ← 流畅度分析（WPM/停顿/口头禅/磕巴）
│   │   └── processor.py        ← 音频管线编排
│   │
│   ├── video/            ← 视频管线
│   │   ├── camera.py           ← OpenCV 摄像头封装（当前未使用，保留备用）
│   │   ├── mediapipe_engine.py ← FaceLandmarker 面部检测（478点+52 blendshapes）
│   │   ├── emotion_analyzer.py ← 情绪提取（紧张/微笑/看镜头/头部稳定）
│   │   └── processor.py        ← 视频管线编排（解码前端 Base64 帧）
│   │
│   ├── llm/              ← LLM 评审管线
│   │   ├── llm_engine.py       ← DeepSeek API 调用（重试3次+fallback）
│   │   ├── prompt_builder.py   ← 组装 Prompt（转写+流畅度+情绪）
│   │   └── persona.py          ← 马斯克角色定义 + 输出 JSON Schema
│   │
│   ├── tts/              ← 语音合成
│   │   └── tts_engine.py       ← Edge TTS 合成（zh-CN-YunxiNeural）
│   │
│   └── output/           ← 输出生成
│       ├── photo_composer.js   ← 合影合成（Pillow，叠加签名+logo+结语）
│       ├── qr_generator.py     ← 二维码生成（qrcode 库）
│       └── h5_generator.py     ← H5 评审报告页面（单页 HTML）
│
├── services/             ← 业务服务
│   ├── pipeline_orchestrator.py ← 三管线调度器（录制→分析→输出）
│   ├── signal_quality.py       ← 信号质量评估
│   └── degradation.py          ← 降级策略
│
├── data/                 ← 运行时数据（.gitignore）
│   ├── audio/            ← 录音 WAV 文件
│   ├── photos/           ← 合影 JPG 文件
│   ├── qr/               ← 二维码 PNG 文件
│   └── h5/               ← H5 HTML 文件
│
└── assets/               ← 素材
    ├── musk_signature.png
    └── event_logo.png
```

### 后端核心流程

```
main.py（接收 HTTP）
  │
  ▼
orchestrator（调度）
  ├── 音频管线 → recorder → whisper_engine → fluency_analyzer
  ├── 视频管线 → 前端帧 → mediapipe_engine → emotion_analyzer
  └── LLM 管线 → prompt_builder → llm_engine → review
  │
  ▼
输出管线 → photo_composer + qr_generator + h5_generator
  │
  ▼
SSE 推送给前端
```

---

## frontend/ — 前端（React + Vite + TailwindCSS）

```
frontend/
├── vite.config.ts         ← Vite 配置（代理 /api + /static 到后端）
├── tsconfig.json          ← TypeScript 配置
├── package.json           ← npm 依赖
│
└── src/
    ├── main.tsx           ← React 入口
    ├── App.tsx            ← 根组件（按 step 切换 5 个页面）
    ├── index.css          ← TailwindCSS
    │
    ├── pages/             ← 5 个页面 = 5 步状态机
    │   ├── Welcome.tsx        ← 欢迎页 + 10s 倒计时
    │   ├── Presenting.tsx     ← Start→录音+发帧+摄像头+倒计时→End Early
    │   ├── Thinking.tsx       ← 分析中动画（自动跳转）
    │   ├── Reviewing.tsx      ← 5 段评审卡片
    │   └── PhotoOutput.tsx    ← 合影 + 二维码
    │
    ├── components/        ← 共享组件
    │   ├── Countdown.tsx      ← 倒计时动画（最后 10s 变红）
    │   ├── ReviewCard.tsx     ← 评审卡片（insight/list/quote 三种样式）
    │   └── QRDisplay.tsx      ← 二维码展示 + 扫码提示
    │
    ├── stores/            ← 状态管理
    │   └── boothStore.ts      ← Zustand（step + data + updateFromSSE）
    │
    └── hooks/             ← 自定义 Hooks
        └── useBoothSSE.ts     ← SSE EventSource 连接 + 3s 自动重连
```

### 前端页面跳转

```
Welcome（倒计时 10s）
  │ SSE 推送 step=presenting
  ▼
Presenting（Start 按钮 → 录音+发帧+60s 倒计时）
  │ End Early / 倒计时归零
  ▼
Thinking（"Analyzing with first principles..."）← 自动跳转
  │ 三管线完成 → 自动 step=reviewing
  ▼
Reviewing（5 段评审卡片）
  │ Continue to Photo
  ▼
PhotoOutput（合影 + 二维码 + H5）
  │ Start Again（页面重载）
  ▼
Welcome ...
```

---

## 状态机与数据流

```
Step       前端显示        后端处理             数据
──────     ────────       ────────           ────
welcome   欢迎页 10s     重置会话              -
presenting 录音+摄像头    录音 60s + 收帧     WAV + frames
thinking  分析动画        三管线并行分析       fluency/emotion/review
reviewing 评审卡片        -                   评审数据已就绪
photo     合影+二维码    生成合影/QR/H5       photo/qr 路径
complete  同 photo        -                   -
```

### 数据采集方式

| 数据 | 来源 | 采集方式 |
|------|------|---------|
| 音频 | PyAudio 麦克风 | 后端回调模式录制 60s |
| 视频帧 | 浏览器摄像头 | 前端 canvas 截图 → Base64 JPEG → POST 到后端 |
| 情绪 | 视频帧 → MediaPipe | FaceLandmarker 478 点 + 52 blendshapes |
| 评审 | DeepSeek API | 转写文本 + 流畅度 + 情绪 → LLM 生成 |

---

## 关键配置（backend/config.py）

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | 环境变量 | DeepSeek API Key |
| `LLM_API_URL` | `https://api.deepseek.com/v1/chat/completions` | API 地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名 |
| `EDGE_TTS_VOICE` | `zh-CN-YunxiNeural` | TTS 语音 |
| `CAMERA_INDEX` | 0 | 摄像头索引（当前未使用） |
| `AUDIO_DURATION` | 60 | 录音最长秒数 |
| `VIDEO_FPS` | 5 | 帧率 |
| `DEBUG_MODE` | True（环境变量 `DEBUG=1`） | 调试输出开关 |

---

## 旧版备份（hackathon/ 目录）

`hackathon/hackathon/` 和 `hackathon/hackathon/hks/` 是之前打包分发的旧版本，**当前开发以根目录 `hks/` 为准**，旧版可删除。
