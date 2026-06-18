# JudgeBooth — 传奇评审亭 🎤🤖

> **AI 马斯克评审亭**：站到摄像头前展示你的黑客松项目，获得马斯克风格的硬核评审报告 + Polaroid 纪念合影。

---

## 📋 项目介绍

JudgeBooth 是一个沉浸式的 AI 评审体验应用。你站在摄像头前用 60 秒介绍你的项目，系统会：

1. 🎙️ **实时语音识别** — Soniox WebSocket 流式转写你的演讲
2. 👁️ **面部表情分析** — MediaPipe 478 点面部网格 + 52 组 ARKit blendshapes
3. 🧠 **LLM 评审** — DeepSeek 以"马斯克五维思维模型"生成硬核评审
4. 🔊 **马斯克朗读** — Edge TTS 中英双语独白（中文男声 + 英文马斯克味）
5. 📸 **AI 换头合影** — 阿里云 Wan2.7-Image 将你融入 Polaroid 风格纪念卡

全程 5 步状态机：**Welcome → Presenting → Thinking → Reviewing → PhotoOutput**

---

## 🚀 快速开始

### 前置要求

| 软件 | 版本 |
|------|------|
| Python | 3.10+ |
| Node.js | 18+ |
| pip + npm | 最新 |

### 1️⃣ 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt  # 或直接双击 setup.bat

# 前端
cd frontend
npm install
```

### 2️⃣ 配置环境变量

> ⚠️ **务必替换为你的真实 API Key！**

| 变量 | 必须 | 说明 | 获取方式 |
|------|------|------|---------|
| `LLM_API_KEY` | ✅ | DeepSeek API（评审用） | [platform.deepseek.com](https://platform.deepseek.com) |
| `IMG_GEN_API_KEY` | ✅ | 阿里云 Wan2.7-Image（换头） | [dashscope.aliyun.com](https://dashscope.aliyun.com) |
| `SONIOX_API_KEY` | ⚠️ | Soniox 实时语音识别 | [soniox.com](https://soniox.com) |
| `PUBLIC_HOST` | ⚠️ | AI 生图需要公网 URL | ngrok 地址（见下文） |

### 3️⃣ 启动（三个终端）

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

**终端 3 — ngrok（AI 生图需要公网访问本地图片）**
```bash
D:\ngrok\ngrok.exe http 8000
# 看到 Forwarding https://xxx.ngrok-free.dev 后，停掉后端加上 PUBLIC_HOST 重启：
$env:PUBLIC_HOST = "https://xxx.ngrok-free.dev"
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4️⃣ 使用流程

| 页面 | 说明 |
|------|------|
| **Welcome** | 3.5s 加载动画 → 自动跳转路演 |
| **Presenting** | 点 **开始路演** → 对着摄像头讲（最多 60s）→ **结束路演** |
| **Thinking** | 三管线并行分析（语音/视频/LLM → TTS），自动跳转 |
| **Reviewing** | 马斯克评审卡片 + 你的表现数据面板 + ▶ 听他说 |
| **PhotoOutput** | AI 换头 Polaroid 纪念卡 + 二维码 → 重新开始 |

---

## 🏗️ 项目结构

```
hks/
├── backend/                      # Python FastAPI 后端
│   ├── main.py                  # HTTP + SSE + 5 步状态机
│   ├── config.py                # 配置常量
│   ├── debug_utils.py           # 统一调试日志
│   ├── models/
│   │   └── session.py          # BoothSession 会话状态
│   ├── pipelines/
│   │   ├── audio/              # 录音(Soniox/Whisper) + 流畅度分析
│   │   ├── video/              # FaceLandmarker → 情绪分析
│   │   ├── llm/                # 提示词构建 → DeepSeek 评审
│   │   ├── tts/                # Edge TTS 马斯克朗读
│   │   └── output/             # AI 生图 + QR + H5
│   ├── services/
│   │   └── pipeline_orchestrator.py  # 三管线调度
│   └── data/                   # 输出文件（音频/照片/QR/H5）
├── frontend/                    # React 18 + Vite + TailwindCSS
│   └── src/
│       ├── pages/              # 5 个页面组件
│       ├── components/         # MuskPresence / ReviewCard / QRDisplay
│       ├── stores/             # Zustand boothStore
│       └── hooks/              # useBoothSSE / useSoniox / useFaceMesh
├── docs/                        # 开发文档
├── setup.bat                    # 一键安装脚本
├── start.bat                    # 后端启动脚本
└── start-frontend.bat           # 前端启动脚本
```

---

## 🧠 技术栈

| 模块 | 技术 |
|------|------|
| **后端框架** | Python FastAPI + SSE (sse-starlette) |
| **前端框架** | React 18 + Vite + TailwindCSS + Framer Motion + Zustand |
| **语音识别** | Soniox stt-rt-v5（云端，实时流式） / faster-whisper 降级 |
| **面部检测** | MediaPipe FaceLandmarker（478 点 + 52 ARKit blendshapes） |
| **LLM 评审** | DeepSeek API（OpenAI 兼容格式，deepseek-chat） |
| **语音合成** | Edge TTS（中文 zh-CN-YunjianNeural + 英文 en-US-ChristopherNeural） |
| **AI 合影** | 阿里云 Wan2.7-Image（多图参考换头换装） / Pillow 降级 |
| **调试系统** | debug_utils 统一日志（[STEP]/[DATA]/[ERROR] 标记） |

---

## 🔑 API Key 获取

### DeepSeek
1. 访问 [platform.deepseek.com](https://platform.deepseek.com) 注册
2. 进入 API Keys 页面创建 Key，以 `sk-` 开头
3. 余额充值即可调用

### 阿里云 DashScope（Wan2.7-Image）
1. 访问 [dashscope.aliyun.com](https://dashscope.aliyun.com) 登录
2. 进入 API Key 管理创建 Key
3. 开通"通义万相"服务

### Soniox（实时语音识别，可选）
1. 访问 [soniox.com](https://soniox.com) 注册
2. 进入 Dashboard 获取 API Key
3. 如不配置则降级使用 faster-whisper 本地识别（效果较差）

---

## 📝 常见问题

**Q: AI 生图一直失败？**
A: 确保设置了 `PUBLIC_HOST` 为公网可访问的 ngrok 地址，否则阿里云 API 无法下载你的照片。

**Q: 摄像头打不开？**
A: 浏览器需要授予摄像头权限，确保使用 HTTPS 或 localhost，建议用 Chrome。

**Q: 录音没有识别？**
A: 检查 Soniox API Key 是否配置正确；未配置时会降级为 faster-whisper，需要安装 CTranslate2。

**Q: TypeScript 编译报错？**
A: 在 `frontend/` 目录运行 `npx tsc --noEmit` 检查，确保 `@soniox/speech-to-text-web` 等依赖已安装。

---

## 📄 开源协议

MIT

---

*Made with ❤️ for Hackathon*
