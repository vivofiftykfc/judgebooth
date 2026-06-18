# 主干调试操作手册

> **目标**: 三个人一台机，一次走通全流程
> **预估时间**: 30 分钟
> **环境**: Windows + 摄像头 + 麦克风 + 大屏幕

---

## Step 0：清理环境（A 执行）

```bash
taskkill /f /im python.exe 2>nul
taskkill /f /im uvicorn.exe 2>nul
taskkill /f /im node.exe 2>nul
netstat -ano | findstr ":8000" || echo "8000 空闲"
netstat -ano | findstr ":5173" || echo "5173 空闲"
```

---

## Step 1：安装依赖（A 执行，B+C 确认无报错）

```bash
cd D:\hks\backend && pip install -r requirements.txt
cd D:\hks\frontend && npm install
```

三人确认日志末尾**没有 ERROR/FAILED**。

---

## Step 2：启动后端（A 执行）

```bash
set LLM_API_KEY=sk-6e863dcd99a94c63a7065c43cadc4cbe
cd D:\hks\backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

**确认看到：**
```
Camera opened successfully.
Uvicorn running on http://0.0.0.0:8000
```

---

## Step 3：启动前端（C 执行，另开终端）

```bash
cd D:\hks\frontend
npm run dev
```

浏览器打开 `http://localhost:5173` → **黑底白字"欢迎来到 X.AI 临时评审室"**

---

## Step 4：测后端连通性（C 在浏览器执行）

```
http://localhost:8000/api/health
```

**预期：** `{"status":"ok"}`

---

## Step 5：走 5 步流程（三个人一起盯屏幕）

| 操作者 | 执行命令 | 屏幕预期 |
|--------|---------|---------|
| C | 打开浏览器 | 欢迎页 + 10s 倒计时 |
| A | `curl -X POST localhost:8000/api/step/welcome` | 重置 |
| A | `curl -X POST localhost:8000/api/step/presenting/start` | 路演页 120s 倒计时 |
| 全员 | *等待 5 秒* | — |
| A | `curl -X POST localhost:8000/api/step/presenting/end` | 思考动画页 |
| 全员 | *等待 30-60 秒（管线并行）* | 思考动画 |
| A | `curl -X POST localhost:8000/api/step/thinking/complete` | 评审宣读页 |
| A | `curl -X POST localhost:8000/api/step/reviewing/complete` | 合影二维码页 |
| A | `curl -X POST localhost:8000/api/step/photo/complete` | 完成页 |

---

## Step 6：验证管线数据（A 执行）

```bash
curl -s http://localhost:8000/api/stream | head -5
```

检查 JSON 中 data 字段：

| 字段 | 应该有值 | 含义 |
|------|---------|------|
| `data.transcript` | 路演转写文本 | Whisper 转写成功 |
| `data.fluency` | WPM / pause_count | 流畅度分析成功 |
| `data.emotion` | tension_index / smile_index | 情绪提取成功 |
| `data.review` | insight / highlights | LLM 评审成功 |

---

## 排查对照表

| 现象 | 问题 | 谁负责 |
|------|------|--------|
| `transcript` 为 null | Whisper 模型未下载 / 麦克风没声音 | **A** |
| `emotion` 为 null | MediaPipe 人脸检测失败 | **B** |
| `review` 为 fallback | LLM_API_KEY 未设 | **A** |
| 前端白屏 | Vite 未启动 / proxy 不对 | **C** |
| 摄像头红灯不亮 | index 不对 / 驱动 | **B** |

---

## 常见问题速查

| 问题 | 解决 |
|------|------|
| faster-whisper 首次加载慢 | ~20s 正常 |
| LLM 返回占位评审 | `set LLM_API_KEY=sk-xxx` 后重启 |
| 摄像头读不到 | 改 `config.py` 中 `CAMERA_INDEX` |
| 端口被占用 | `taskkill /f /im python.exe` 重试 |
