# JudgeBooth — 传奇评审亭 🎤🤖

> **AI 马斯克评审亭**：站到摄像头前展示你的黑客松项目，获得马斯克风格的硬核评审报告 + Polaroid 纪念合影。

---

## 📋 项目介绍

JudgeBooth 是一个沉浸式 AI 评审体验应用。你站在摄像头前用 60 秒介绍你的项目，系统会：

| 步骤 | 说明 |
|------|------|
| 🎙️ **实时语音识别** | Soniox WebSocket 流式转写你的演讲（中文+英文） |
| 👁️ **面部表情分析** | MediaPipe 478 点面部网格 + 52 组 ARKit blendshapes |
| 🧠 **LLM 评审** | DeepSeek 以"马斯克五维思维模型"生成硬核评审报告 |
| 🔊 **马斯克朗读** | Edge TTS 中英双语独白（中文男声 + 英文低沉男声） |
| 📸 **AI 换头合影** | 阿里云 Wan2.7-Image 将你完整替换进 Polaroid 风格纪念卡 |

**5 步状态机：** Welcome → Presenting → Thinking → Reviewing → PhotoOutput

---

## 🚀 快速部署

### 前置条件

| 依赖 | 版本 | 下载 |
|------|------|------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| Git | 任意 | [git-scm.com](https://git-scm.com/) |

### 1️⃣ 克隆项目

```bash
git clone https://github.com/vivofiftykfc/judgebooth.git
cd judgebooth
```

### 2️⃣ 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd ../frontend
npm install
```

### 3️⃣ 配置环境变量

> ⚠️ **必须将以下 API Key 替换为你自己的密钥！**

| 变量 | 必须 | 用途 | 获取地址 |
|------|------|------|---------|
| `LLM_API_KEY` | ✅ | DeepSeek API 评审 | [platform.deepseek.com](https://platform.deepseek.com) |
| `IMG_GEN_API_KEY` | ✅ | 阿里云 Wan2.7 换头 | [dashscope.aliyun.com](https://dashscope.aliyun.com) |
| `SONIOX_API_KEY` | ❌ | Soniox 实时语音（不设则降级 faster-whisper） | [soniox.com](https://soniox.com) |
| `PUBLIC_HOST` | ⚠️ | AI 生图需要公网 URL（见 ngrok 说明） | ngrok 地址 |

### 4️⃣ 启动服务

需要开启 **三个终端**：

**终端 1 — 后端**
```bash
cd backend

# Windows CMD
set LLM_API_KEY=your_deepseek_api_key
set IMG_GEN_API_KEY=your_wan_api_key
set KMP_DUPLICATE_LIB_OK=TRUE
uvicorn main:app --host 0.0.0.0 --port 8000

# PowerShell
$env:LLM_API_KEY = "your_deepseek_api_key"
$env:IMG_GEN_API_KEY = "your_wan_api_key"
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
uvicorn main:app --host 0.0.0.0 --port 8000
```

**终端 2 — 前端**
```bash
cd frontend
npm run dev
```

浏览器打开 **http://localhost:5173**

**终端 3 — ngrok（可选，AI 合影需要公网访问本地图片）**
```bash
D:\ngrok\ngrok.exe http 8000
# 看到 Forwarding https://xxx.ngrok-free.dev 后，
# 停掉终端 1 的后端，加上 PUBLIC_HOST 重开：
$env:PUBLIC_HOST = "https://xxx.ngrok-free.dev"
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 🎮 使用流程

| 页面 | 操作 |
|------|------|
| **Welcome** | 3.5s 加载动画 → 自动跳转路演 |
| **Presenting** | 点 **开始路演** → 对着摄像头讲（最多 60s）→ **结束路演** |
| **Thinking** | 三管线并行分析（语音 → 视频 → LLM → TTS），自动跳转 |
| **Reviewing** | 马斯克评审卡片 + 🔊 听他说 + 你的表现数据面板 |
| **PhotoOutput** | AI 换头 Polaroid 纪念卡 + 二维码 → **重新开始** |

---

## 🏗️ 项目结构

```
hks/
├── backend/                      # Python FastAPI
│   ├── main.py                  # HTTP API + SSE 状态推送
│   ├── config.py                # 配置常量
│   ├── debug_utils.py           # 统一调试日志
│   ├── models/
│   │   ├── session.py          # BoothSession 会话状态
│   │   ├── review.py           # 评审报告 Schema
│   │   └── performance.py      # FluencyReport + EmotionReport
│   ├── pipelines/
│   │   ├── audio/              # 录音 + Whisper/Soniox + 流畅度
│   │   ├── video/              # FaceLandmarker + 情绪分析
│   │   ├── llm/                # 提示词构建 + DeepSeek API
│   │   ├── tts/                # Edge TTS 马斯克朗读
│   │   └── output/             # AI 生图 + QR + H5
│   ├── services/
│   │   └── pipeline_orchestrator.py  # 三管线调度
│   └── data/                   # 运行时输出（音频/照片/QR/H5）
├── frontend/                    # React 18 + Vite
│   └── src/
│       ├── pages/              # 5 个页面组件
│       ├── components/         # MuskPresence / ReviewCard 等
│       ├── stores/             # Zustand 状态管理
│       └── hooks/              # SSE / Soniox / FaceMesh
├── docs/                        # 开发文档、PRD、调试教程
├── setup.bat                    # 一键安装依赖
├── start.bat                    # 后端快速启动
└── start-frontend.bat           # 前端快速启动
```

---

## 🧠 技术栈

| 模块 | 技术 |
|------|------|
| **后端框架** | Python FastAPI + sse-starlette |
| **前端框架** | React 18 + Vite + TailwindCSS + Framer Motion + Zustand |
| **语音识别** | Soniox stt-rt-v5（云端实时） / faster-whisper（本地降级） |
| **面部检测** | MediaPipe FaceLandmarker（478 点 + 52 blendshapes） |
| **LLM 评审** | DeepSeek API（OpenAI 兼容格式，deepseek-chat） |
| **语音合成** | Edge TTS（zh-CN-YunjianNeural + en-US-ChristopherNeural） |
| **AI 合影** | 阿里云 Wan2.7-Image（多图参考换头换装） / Pillow 降级 |
| **调试系统** | debug_utils 统一日志（[STEP] / [DATA] / [ERROR] 标记） |

---

## 🔑 API Key 获取指南

### DeepSeek
1. 注册 [platform.deepseek.com](https://platform.deepseek.com)
2. 进入 **API Keys** 页面创建 Key（以 `sk-` 开头）
3. 充值即可调用

### 阿里云 DashScope（Wan2.7-Image）
1. 登录 [dashscope.aliyun.com](https://dashscope.aliyun.com)
2. 进入 **API Key 管理** 创建 Key
3. 开通 **通义万相** 服务

### Soniox（可选，推荐）
1. 注册 [soniox.com](https://soniox.com)
2. 进入 Dashboard 获取 API Key
3. 不配置则自动降级为 faster-whisper 本地识别

---

## ❓ 常见问题

**Q: AI 合影一直失败？**
A: 确认已设置 `PUBLIC_HOST` 为公网可访问地址（ngrok），否则阿里云无法下载你的照片。

**Q: 摄像头不工作？**
A: 浏览器需授予摄像头权限，建议用 Chrome 并通过 localhost 访问。

**Q: 语音识别没反应？**
A: 检查 Soniox API Key；未配置时会降级 faster-whisper，需确保已安装 CTranslate2。

**Q: 前端编译报错？**
A: 在 `frontend/` 目录运行 `npm install` 确保依赖完整，然后 `npx tsc --noEmit` 检查。

---

## 📄 协议

MIT

---

*Made with ❤️ for Hackathon*
