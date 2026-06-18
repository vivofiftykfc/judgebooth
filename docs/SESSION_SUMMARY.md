# 传奇评审亭 — 阶段总结文档

> **会话时间**: 2026-06-17
> **项目状态**: 第一版开发完成，联调通过
> **总代码量**: ~4000 行（后端 2700 + 前端 700 + 配置/文档 600）

---

## 一、我们做了什么

### 阶段 1：需求理解与文档化

你提供了原始 PRD 草稿（AI 马斯克评审亭的概念），我理解并补充了完整的 5 步流程、AI 角色设定、技术架构，输出了 3 份文档：

| 文档 | 内容 | 行数 |
|------|------|------|
| `PRD.md` | 产品需求文档（问题陈述、体验旅程、技术架构、交付物） | 271 |
| `IMPLEMENTATION.md` | 技术实现方案（管线设计、算法细节、目录结构） | 1097 |
| `IMPLEMENT_PLAN.md` | 多 Agent 并行执行计划（波次分解、Agent 分工） | 399 |

关键的三个决定：
- **删了马斯克声线克隆**（太复杂，Edge TTS 就够）
- **自信度分析简化为情绪指标**（MediaPipe 52 blendshapes 直接拿来用）
- **不缝开源项目**，核心逻辑自己写，保持可控

---

### 阶段 2：项目骨架搭建（Wave 0）

创建了完整的目录结构、配置文件和基础设施：

```
hks/
├── docker-compose.yml          # whisper-live 服务
├── .gitignore / CLAUDE.md
├── backend/                    # Python FastAPI 后端
│   ├── main.py + config.py     # 入口 + 配置
│   ├── models/                 # 3 个数据模型
│   ├── pipelines/              # 5 个管线（audio/video/llm/tts/output）
│   └── services/               # 3 个服务（orchestrator/quality/degradation）
├── frontend/                   # React + Vite + TailwindCSS 前端
│   └── src/                    # 5 页面 + 3 组件 + 1 store + 1 hook
├── PRD.md / IMPLEMENTATION.md / IMPLEMENT_PLAN.md / DEBUG_PLAN.md
└── SESSION_SUMMARY.md
```

---

### 阶段 3：后端核心开发（Wave 1）

**2 个 Agent 并行运行**：

| Agent | 产出 | 文件数 |
|-------|------|--------|
| Agent A（FastAPI 主应用） | main.py, config.py, 3 个 models, 3 个 services | 8 |
| Agent B（音频管线） | recorder.py, whisper_engine.py, fluency_analyzer.py, processor.py | 4 |

审查发现 import 路径不一致（并行开发的经典问题），手动修复后提交。

---

### 阶段 4：视觉 + LLM + 输出开发（Wave 2）

**2 个 Agent 并行运行**：

| Agent | 产出 | 文件数 |
|-------|------|--------|
| Agent C（视频管线） | camera.py, mediapipe_engine.py, emotion_analyzer.py, processor.py | 4 |
| Agent D（LLM+TTS+输出） | persona.py, prompt_builder.py, llm_engine.py, tts_engine.py, photo_composer.py, qr_generator.py, h5_generator.py | 7 |

全部 Python 语法检查通过。

---

### 阶段 5：前端开发（Wave 3）

**1 个 Agent** 创建了 11 个前端文件：

- 5 个页面组件（Welcome / Presenting / Thinking / Reviewing / PhotoOutput）
- 3 个共享组件（Countdown / ReviewCard / QRDisplay）
- 1 个 Zustand Store + 1 个 SSE Hook
- TypeScript 编译零错误，Vite 构建 2.21s

---

### 阶段 6：联调与修复

发现并修复了 6 个关键问题：

| # | 问题 | 修复 |
|---|------|------|
| 1 | LLM API 格式不兼容（Anthropic vs OpenAI） | 改为 OpenAI 兼容格式适配 DeepSeek |
| 2 | Whisper 依赖 Docker | 改为本地 faster-whisper |
| 3 | TTS 语音名 `zh-CN-Yunxi` 格式错误 | 改为 `zh-CN-YunxiNeural` |
| 4 | emotion_analyzer 只接受 dict，MediaPipe 返回对象 | 加 `hasattr` 兼容两种格式 |
| 5 | photo_composer 参数签名不匹配 | 改为全部可选参数 |
| 6 | 摄像头被进程锁住 | wmic 强制释放 + cleanup |

---

### 阶段 7：三人分工调试计划

创建了 `DEBUG_PLAN.md`（630 行），将调试分为三部分：

| 角色 | 模块 | 测试重点 |
|------|------|---------|
| **A** 🎤 | 音频 + LLM + TTS | 录音/转写/流畅度/评审/播报 |
| **B** 📷 | 视觉 + 输出 | 摄像头/FaceLandmarker/情绪/合影/QR |
| **C** 🖥️ | 前端 + H5 | 5 页面/SSE/动画/H5 渲染 |

每人有 Step-by-step 测试、输入输出验收标准、常见问题排雷。

---

### 阶段 8：各角色独立测试

| 测试项 | A 角 | B 角 | C 角 |
|--------|------|------|------|
| 依赖/环境 | ✅ | ✅ OpenCV+MediaPipe | ✅ npm build |
| 音频录制 | ✅ 160KB WAV | — | — |
| 流畅度分析 | ✅ WPM/停顿/口头禅 | — | — |
| LLM 评审 | ✅ DeepSeek API 已通 | — | — |
| TTS 合成 | ✅ 295KB MP3 | — | ✅ 渲染通过 |
| 摄像头 | — | ✅ index 0, 640x480 | — |
| FaceLandmarker | — | ✅ 478 点 + 52 blendshapes | — |
| 情绪提取 | — | ✅ 紧张/微笑度 0-1 | — |
| 合影+QR | — | ✅ 56KB + 1.2KB | — |
| 5 页面 UI | — | — | ✅ 32/32 检查通过 |
| H5 生成 | — | — | ✅ 4144 字符 |
| 后端端点 | ✅ 全部 6 个 200 | — | — |
| 端到端联调 | ✅ 全流程 | ✅ 全流程 | ✅ 全流程 |

---

## 二、最终架构图

```
┌─ 用户 ───────────────────────────────┐
│   进入评审亭 → 路演 120s → 合影打卡   │
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│         前端 React (localhost:5173)    │
│  Welcome → Presenting → Thinking →   │
│  Reviewing → PhotoOutput             │
│          ▲ SSE 实时推送               │
└──────────────────┬───────────────────┘
                   │ HTTP / SSE
┌──────────────────▼───────────────────┐
│     FastAPI 后端 (localhost:8000)     │
│                                      │
│   ┌──────────────────────────────┐   │
│   │    Pipeline Orchestrator      │   │
│   └──────┬──────────┬───────────┘   │
│          │          │               │
│   ┌──────▼──┐ ┌─────▼──────┐       │
│   │ 音频管线 │ │ 视频管线    │       │
│   │ -recorder│ │ -camera    │       │
│   │ -whisper │ │ -mediapipe │       │
│   │ -fluency │ │ -emotion   │       │
│   └──────┬──┘ └─────┬──────┘       │
│          │          │               │
│   ┌──────▼──────────▼──────┐       │
│   │      LLM 管线          │       │
│   │  prompt_builder →      │       │
│   │  DeepSeek API → 评审    │       │
│   └──────────┬─────────────┘       │
│              │                     │
│   ┌──────────▼─────────────┐       │
│   │  输出管线              │       │
│   │  TTS + 合影 + QR + H5  │       │
│   └────────────────────────┘       │
└────────────────────────────────────┘
```

---

## 三、项目现状

### ✅ 已完成
- 全部 23 个后端 Python 文件（语法检查通过）
- 全部 12 个前端 TypeScript/TSX 文件（编译通过）
- 5 份文档（PRD / IMPLEMENTATION / IMPLEMENT_PLAN / DEBUG_PLAN / CLAUDE）
- 6 个 API 端点正常响应
- DeepSeek API 集成可发真实评审
- faster-whisper 本地转写就绪
- MediaPipe FaceLandmarker 情绪提取工作
- 合影 + 二维码 + H5 生成验证通过

### ⚠️ 启动前别忘了
```bash
# 设 API Key（否则 LLM 走 fallback 占位评审）
export LLM_API_KEY=sk-6e863dcd99a94c63a7065c43cadc4cbe

# 启动后端
cd D:/hks/backend && uvicorn main:app --host 0.0.0.0 --port 8000

# 启动前端
cd D:/hks/frontend && npm run dev
```

### 📋 待办
| 事项 | 优先级 |
|------|--------|
| 设 LLM_API_KEY 环境变量 | **P0（每次启动必做）** |
| 首次运行等待 faster-whisper 下载模型 | P1 |
| 女娲.skill 接入（替换 persona.py 占位） | P2 |
| 物理评审亭搭建（屏幕/摄像头/麦克风/灯光） | 你的工作 |

---

## 四、文件统计

```
总计 55 个文件，3732 行代码

后端 Python:  23 个文件，2729 行
前端 TS/TSX:  12 个文件，681 行
文档 MD:       5 个文件，2447 行
配置文件:      7 个文件
基础设施:      5 个文件
```
