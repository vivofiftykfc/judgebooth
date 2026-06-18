# 🍼 保姆级调试教程手册

> 本文档教你如何读懂终端的调试输出，快速定位问题。
> **关键词**: `[DEBUG]` `[STEP]` `[DATA]` `[ERROR]` — 看这些标记找问题。

---

## 一、调试输出格式速查

启动后端后，终端会实时打印形如以下的调试信息：

```
  >>> [STEP][10:15:30.123][MAIN] === Step: welcome ===
  [DEBUG][10:15:30.124][MAIN] 重置会话，设置 10s 倒计时
  [DATA][10:15:30.125][MAIN] session.transcript = <None>
  >>> !!! [ERROR][10:15:30.126][WHISPER] 音频文件不存在
```

| 前缀 | 含义 | 什么情况下看 |
|------|------|-------------|
| `>>> [STEP]` | **步骤切换** — 标记重要的阶段变化 | 看流程走到哪一步了 |
| `[DEBUG]` | **常规调试** — 告诉你代码在做什么 | 看具体执行细节 |
| `[DATA]` | **关键数据** — 显示变量值/长度/类型 | 看数据有没有传过来 |
| `>>> !!! [ERROR]` | **错误** — 出问题了 | 看哪里崩了 |
| `[MAIN]` | **模块标签** — 这段日志来自哪个模块 | 定位问题属于哪个环节 |

### 模块标签对照表

| 标签 | 模块 | 负责什么 |
|------|------|---------|
| `MAIN` | main.py | API 端点、SSE 推送 |
| `ORCH` | pipeline_orchestrator.py | 三管线调度 |
| `AUDIO` | audio/processor.py | 音频管线总控 |
| `RECORDER` | audio/recorder.py | 麦克风录音 |
| `WHISPER` | audio/whisper_engine.py | 语音转写 |
| `CAMERA` | video/camera.py | 摄像头录制 |
| `MEDIAPIPE` | video/mediapipe_engine.py | 面部检测 |
| `EMOTION` | video/emotion_analyzer.py | 情绪提取 |
| `PROMPT` | llm/prompt_builder.py | Prompt 组装 |
| `LLM` | llm/llm_engine.py | LLM API 调用 |
| `TTS` | tts/tts_engine.py | 语音合成 |
| `PHOTO` | output/photo_composer.py | 合影合成 |
| `QR` | output/qr_generator.py | 二维码 |
| `H5` | output/h5_generator.py | H5 页面 |

---

## 二、正常流程 Debug 输出全览

### 启动阶段
```
  >>> [STEP][MAIN] === 服务启动 ===
  Camera opened successfully.
  Uvicorn running on http://0.0.0.0:8000
```

### Step 1 — Welcome（重置会话）
```
  >>> [STEP][MAIN] === Step: welcome ===
  [DEBUG][MAIN] 重置会话，设置 10s 倒计时
  [DEBUG][MAIN] welcome 完成，当前 step=presenting
```

### Step 2 — Presenting/Start（录制开始）
```
  >>> [STEP][MAIN] === Step: presenting/start ===
  [DEBUG][MAIN] 开始录制，倒计时=120s
    >>> [STEP][ORCH] === 启动录制 ===
    [DEBUG][ORCH] 开始录音（120s, 16kHz）...
      >>> [STEP][RECORDER] 录音文件: recording_20260617_120000.wav
    [DEBUG][RECORDER] PyAudio 初始化完成，设备数: 3
    [DEBUG][RECORDER] 默认麦克风: Microphone (Realtek Audio)
    [DEBUG][RECORDER] 开始录音: 120s, 共 1875 块
    [DEBUG][RECORDER] 录音进度: 25% (468/1875 块)
    [DEBUG][RECORDER] 录音进度: 50% (937/1875 块)
    [DEBUG][RECORDER] 录音进度: 75% (1406/1875 块)
    [DEBUG][ORCH] 录音完成，耗时 120.5s
    [DEBUG][ORCH] 文件: xxx.wav (1.9 MB)
```

### Step 3 — Presenting/End（录制完成 → 分析）
```
  >>> [STEP][MAIN] === Step: presenting/end ===
    >>> [STEP][ORCH] === 开始分析 ===
    [DEBUG][ORCH] 三管线并行启动...
      >>> [STEP][ORCH] --- 音频管线启动 ---
      >>> [STEP][ORCH] --- 视频管线启动 ---
      >>> [STEP][ORCH] --- LLM 管线启动 ---
```

### 音频管线过程
```
  >>> [STEP][AUDIO] >> 录音阶段
  [DEBUG][AUDIO] 录音完成，耗时 0.1s
    >>> [STEP][AUDIO] >> Whisper 转写阶段
  [DEBUG][WHISPER] 检测语言: zh, 概率: 0.95
  [DEBUG][WHISPER] 转写完成: 25 个片段, 总字符数 342
  [DATA][AUDIO] 转写文本 = '我们这个项目是...' (len=342)
    >>> [STEP][AUDIO] >> 流畅度分析阶段
  [DATA][AUDIO] 流畅度指标 = {14 keys}
    >>> [STEP][AUDIO] === 音频管线完成 ===
```

### 视频管线过程
```
  >>> [STEP][CAMERA] 摄像头录制: 120s, 5fps, 预期 600 帧
  [DEBUG][CAMERA] 录制进度: 25% (150/600 帧)
  [DEBUG][CAMERA] 录制进度: 50% (300/600 帧)
  [DEBUG][CAMERA] 录制进度: 75% (450/600 帧)
    >>> [STEP][CAMERA] 录制完成: 实际 600 帧
    >>> [STEP][VIDEO] >> FaceLandmarker 初始化
  [DEBUG][VIDEO] FaceLandmarker 就绪
    >>> [STEP][VIDEO] >> 逐帧面部检测 (600 帧)
  [DEBUG][VIDEO] 面部检测进度: 30/600 帧 (检测到脸部: 28)
  [DEBUG][VIDEO] 面部检测率: 580/600 (97%)
    >>> [STEP][VIDEO] >> 情绪指标提取
  [DATA][VIDEO] 情绪信号 = {8 keys}
    >>> [STEP][VIDEO] === 视频管线完成 ===
```

### LLM 管线过程
```
  >>> [STEP][PROMPT] === 组装 LLM Prompt ===
  [DATA][PROMPT] transcript 前100字 = '我们这个项目是...'
  [DATA][PROMPT] fluency_report 是否存在 = True
  [DATA][PROMPT] emotion_report 是否存在 = True
    >>> [STEP][LLM] === 评审生成 ===
  [DEBUG][LLM] API URL: https://api.deepseek.com/v1/chat/completions
  [DEBUG][LLM] Model: deepseek-chat
    >>> [STEP][LLM] >> API 调用第 1/3 次尝试
  [DEBUG][LLM] HTTP 响应: status=200, 耗时 3.2s
  [DEBUG][LLM] finish_reason=stop
  [DEBUG][LLM] 响应内容长度: 420 字符
    >>> [STEP][LLM] 评审 JSON 验证通过
```

### Step 4 — Thinking → Reviewing → Photo
```
  >>> [STEP][MAIN] === Step: thinking/complete ===
  [DATA][MAIN] session.transcript = '...' (len=342)
  [DATA][MAIN] session.fluency_report = {14 keys}
  [DATA][MAIN] session.emotion_report = {8 keys}
  [DATA][MAIN] session.review = {5 keys}
  [DATA][MAIN] session.error = <None>

  >>> [STEP][ORCH] === 输出生成 ===
    >>> [STEP][PHOTO] === 合影合成 ===
  [DEBUG][PHOTO] 原始图片尺寸: (1280, 720)
    >>> [STEP][PHOTO] 合影合成完成，耗时 0.3s
    >>> [STEP][QR] === 二维码生成 ===
    >>> [STEP][QR] 二维码生成完成，耗时 0.1s
    >>> [STEP][H5] === H5 页面生成 ===
    >>> [STEP][H5] H5 页面生成完成，耗时 0.05s

  >>> [STEP][MAIN] === Step: photo/complete ===
  [DEBUG][MAIN] 会话完成，photo_path=xxx.jpg, qr_path=xxx.png
```

---

## 三、常见问题排查指南（看 Debug 输出找问题）

### 🔴 问题 1：录音没声音 → transcript 很短/全空白

```
  [DEBUG][WHISPER] 转写完成: 3 个片段, 总字符数 12
  [DATA][AUDIO] 转写文本 = '嗯 嗯 嗯' (len=5)    ← 只录到噪音
```

**解决：** 检查麦克风是否静音，Windows 麦克风权限是否开启

---

### 🔴 问题 2：Whisper 转写失败

```
  >>> !!! [ERROR][WHISPER] faster-whisper 转写失败
  >>> !!! [ERROR][WHISPER] openai-whisper 也未安装
```

**解决：** `pip install faster-whisper` 或 `pip install openai-whisper`

---

### 🔴 问题 3：摄像头没画面

```
  [DEBUG][CAMERA] 录制进度: 25% (150/600 帧)
  [DEBUG][VIDEO] 面部检测进度: 30/600 帧 (检测到脸部: 0)    ← 没检测到脸
```

**解决：** 检查 `CAMERA_INDEX`（0/1/2），确保光线充足、面部正对镜头

---

### 🔴 问题 4：LLM 返回 fallback 评审

```
  >>> !!! [ERROR][LLM] LLM_API_KEY 未设置，使用 fallback 评审
```

**或：**
```
  >>> !!! [ERROR][LLM] API 调用异常: 401 Client Error    ← Key 不对
  >>> !!! [ERROR][LLM] API 调用异常: ConnectError        ← 网络不通
```

**解决：** `set LLM_API_KEY=sk-xxx` 后重启，检查网络

---

### 🔴 问题 5：SSE 前端不更新

```
  [DEBUG][MAIN] SSE 客户端连接，当前队列数: 1      ← 前端连上了
  ...
  [DEBUG][MAIN] SSE 客户端断开，剩余队列: 0        ← 断开了
```

**解决：** 刷新页面，检查浏览器控制台有无 CORS 错误

---

### 🔴 问题 6：合影是纯色/黑屏

```
  [DEBUG][PHOTO] 输入图片: None                     ← 没有摄像头照片！
```

**解决：** 确保视频管线运行正常，检查 CAMERA_INDEX

---

### 🔴 问题 7：模块 ImportError

```
  >>> !!! [ERROR][AUDIO] 模块缺失: No module named 'pyaudio'
  >>> !!! [ERROR][VIDEO] 模块缺失: No module named 'mediapipe'
```

**解决：** `pip install pyaudio mediapipe faster-whisper edge-tts qrcode[pil] httpx`

---

## 四、快速诊断流程图

```
终端输出 → [STEP] 到哪一步了？
  ├─ welcome → ✅
  ├─ presenting/start → 看 RECORDER 日志
  │   ├─ 有录音进度 → 麦克风 ✅
  │   └─ 无进度/报错 → 检查 pyaudio + 麦克风
  ├─ thinking → 看三管线
  │   ├─ AUDIO → 有转写文本？✅/❌
  │   ├─ VIDEO → 面部检测率>50%？✅/❌
  │   └─ LLM →  有 review？✅/fallback？❌
  ├─ reviewing → review 有值？✅/❌
  └─ photo → 看 PHOTO/QR/H5 日志
```

---

## 五、快速自检

```bash
# 检查 LLM API Key
echo %LLM_API_KEY%

# 检查摄像头
python -c "import cv2; cap=cv2.VideoCapture(0); print(cap.isOpened())"

# 检查麦克风
python -c "import pyaudio; p=pyaudio.PyAudio(); print(p.get_device_count())"

# 启动后端（开 DEBUG）
set DEBUG=1
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 六、关掉调试输出

```bash
set DEBUG=0    # Windows CMD 启动前设置
```

---

## 七、还没找到问题？

把终端的完整 `[STEP]` / `[DATA]` / `[ERROR]` 日志贴给我，截图也行，帮你定位。
