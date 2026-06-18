# JudgeBooth — 传奇评审亭

> AI 马斯克评审亭：站到摄像头前展示你的黑客松项目，获得马斯克风格的硬核评审报告 + Polaroid 纪念合影。

---

## 快速开始（空白电脑）

### 1️⃣ 安装基础环境

| 软件 | 下载地址 |
|------|---------|
| Python 3.10+ | https://www.python.org/downloads/ |
| Node.js 18+ | https://nodejs.org/ |

### 2️⃣ 解压项目

```
将 JudgeBooth.rar 解压到 D:\hks\
```

### 3️⃣ 双击 `setup.bat`

自动安装后端和前端依赖，全程无需操作。

### 4️⃣ 启动

**先启动后端** — 双击 `start.bat`，在 CMD 里依次运行：

```cmd
cd D:\hks\backend
set LLM_API_KEY=sk-6e863dcd99a94c63a7065c43cadc4cbe
set IMG_GEN_API_KEY=sk-ws-H.RPDDHXY.Ehye.MEQCIGk-DahELdHB-K0iHJOepNfDDRLQw0XOSXI6l6yCcUTLAiAsQhljMlEm2n69bMne45LcBAB7_oz2R52nsjEA0TOVWQ
set KMP_DUPLICATE_LIB_OK=TRUE
uvicorn main:app --host 0.0.0.0 --port 8000
```

**再启动前端** — 双击 `start-frontend.bat`

浏览器打开 **http://localhost:5173**

---

## 使用流程

| 页面 | 操作 |
|------|------|
| Welcome | 3.5s 开场动画 → 自动跳转 |
| Presenting | 点 **开始路演** → 对着摄像头讲（最多 60s）→ **结束路演** |
| Thinking | 三管线分析中（自动跳转） |
| Reviewing | 展示马斯克评审卡片 → **Continue to Photo** |
| PhotoOutput | Polaroid 合影 + 二维码 → **重新开始** |

---

## 环境变量

| 变量 | 值 | 说明 |
|------|-----|------|
| `LLM_API_KEY` | `sk-6e863dcd99a94c63a7065c43cadc4cbe` | DeepSeek API（评审用） |
| `IMG_GEN_API_KEY` | `sk-ws-H.RPDDHXY...` | 阿里云 Wan2.7-Image（换头用） |
| `KMP_DUPLICATE_LIB_OK` | `TRUE` | 防止 Whisper 崩溃 |
| `PUBLIC_HOST` | `http://localhost:8000` | AI 生图需要公网时改为 ngrok 地址 |

---

## 项目结构

```
hks/
├── backend/          FastAPI 后端
│   ├── main.py      HTTP + SSE + 5 步状态机
│   ├── config.py    配置
│   ├── models/      数据模型
│   ├── pipelines/   管线（audio/video/llm/output/tts）
│   └── services/    三管线调度
├── frontend/         React 前端
│   └── src/
│       ├── pages/    5 个页面
│       ├── components/  组件
│       ├── stores/      Zustand
│       └── hooks/       SSE + 人脸 Mesh
├── docs/             文档
├── patches/          补丁文件
├── setup.bat         一键安装脚本
├── start.bat         后端启动
└── start-frontend.bat  前端启动
```

---

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端 | Python FastAPI + SSE |
| 前端 | React 18 + Vite + TailwindCSS + Framer Motion + Zustand |
| 语音转写 | faster-whisper（本地） |
| 面部检测 | MediaPipe FaceLandmarker（478 点 + 52 blendshapes） |
| LLM 评审 | DeepSeek API |
| AI 合影 | 阿里云 Wan2.7-Image（换头） / Pillow 降级 |
| 调试 | debug_utils 统一日志（[STEP]/[DATA]/[ERROR]） |
