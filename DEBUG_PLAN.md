# 传奇评审亭 — 调试分工手册

> **版本**: v1.0
> **目标**: 三人并行调试，每人一个独立模块，接口契约定死

---

## 总体接口契约（所有人必须遵守）

### 数据结构协议

所有模块之间通过 `BoothSession` 的以下字段传递数据：

```
session.audio_path    → str          → 录音文件路径
session.transcript    → str          → Whisper 转写文本
session.fluency_report → dict        → 流畅度报告（定义见下）
session.emotion_report → dict        → 情绪报告（定义见下）
session.review        → dict         → 评审报告（定义见下）
session.photo_path    → str          → 合影文件路径
session.qr_path       → str          → 二维码文件路径
session.error         → str | None   → 错误信息
```

### 流畅度报告格式 (FluencyReport dict)

```python
{
    "avg_wpm": float,              # 平均语速（词/分钟）
    "pause_count": int,            # 停顿次数（>1.5s）
    "longest_pause_seconds": float, # 最长停顿（秒）
    "filler_word_count": int,      # 口头禅次数
    "filler_examples": list[str],  # 口头禅类型示例
    "stutter_count": int,          # 磕巴次数
    "wpm_volatility": float,       # 语速波动率
    "summary": str,                # 一句话概述
    "score": int,                  # 流畅度综合评分 0-100
}
```

### 情绪报告格式 (EmotionReport dict)

```python
{
    "tension_index": float,        # 紧张度 0-1
    "smile_index": float,          # 微笑度 0-1
    "overall_emotion": str,        # relaxed_confident | slightly_nervous | tense | neutral
    "gaze_at_camera_pct": float,   # 看镜头百分比 0-100
    "head_stability_score": float, # 头部稳定度 0-100
    "summary": str,                # 一句话概述
    "signal_quality": str,         # good | degraded | poor
}
```

### 评审报告格式 (ReviewReport dict)

```python
{
    "insight": str,                # 一句话本质洞察（≤25字）
    "highlights": list[str],       # 2-3 个硬核亮点
    "sharp_question": str,         # 1 个尖锐问题
    "suggestions": list[str],      # 1-2 条硬核建议
    "closing": str,                # 一句结语
}
```

### SSE 推送格式

```python
{
    "step": "welcome|presenting|thinking|reviewing|photo|complete",
    "countdown": int,
    "data": {
        "transcript": str | None,
        "fluency": dict | None,    # FluencyReport 格式
        "emotion": dict | None,    # EmotionReport 格式
        "review": dict | None,     # ReviewReport 格式
        "photo": str | None,
        "qr": str | None,
        "error": str | None,
    }
}
```

### REST API 端点

```
POST /api/step/welcome
POST /api/step/presenting/start
POST /api/step/presenting/end
POST /api/step/thinking/complete
POST /api/step/reviewing/complete
POST /api/step/photo/complete
GET  /api/stream       (SSE)
GET  /api/health
```

---

## 调试任务 A：音频管线 + LLM

### 负责人：A

### 调试文件清单

| 文件 | 行数 | 功能 |
|------|------|------|
| `backend/pipelines/audio/recorder.py` | 149 | 麦克风录制 120s → WAV |
| `backend/pipelines/audio/whisper_engine.py` | 175 | 调用 docker-whisper-live 转写 |
| `backend/pipelines/audio/fluency_analyzer.py` | 415 | 流畅度指标计算 |
| `backend/pipelines/audio/processor.py` | 103 | 音频管线编排入口 |
| `backend/pipelines/llm/llm_engine.py` | 184 | LLM API 调用 |
| `backend/pipelines/llm/prompt_builder.py` | 111 | Prompt 组装 |
| `backend/pipelines/llm/persona.py` | 28 | 马斯克角色定义 |
| `backend/pipelines/tts/tts_engine.py` | 95 | Edge TTS 合成 |
| `backend/config.py` | 24 | 全局配置 |
| `backend/main.py` | 229 | FastAPI + 状态机 |
| `backend/services/pipeline_orchestrator.py` | 170 | 管线调度器 |

### 你需要准备的环境

- ✅ Python 3.11+
- ✅ Docker（运行 whisper-live）
- ✅ 麦克风（USB 或内置）
- ✅ **LLM API Key**（Anthropic 或兼容 API）

### 测试步骤

#### Step A-1：验证依赖安装

```bash
cd D:/hks/backend
pip install -r requirements.txt
python -c "import pyaudio; print('PyAudio OK')"
python -c "import httpx; print('httpx OK')"
```

**预期**: 全部成功，不报错

---

#### Step A-2：启动 whisper-live

```bash
cd D:/hks
docker compose up -d
sleep 5
curl http://localhost:9090/health
```

**预期**: 返回 `{"status":"ok"}` 或类似健康检查响应

**如果 Docker 不可用** → 修改 `config.py`，把 `WHISPER_URL` 改成测试模式:
```python
# config.py 中加
WHISPER_MOCK = True  # 设为 True 跳过真实 API 调用
```

---

#### Step A-3：测试录音模块（独立）

```python
import asyncio
from pipelines.audio.recorder import record_audio

path = asyncio.run(record_audio(duration=5, sample_rate=16000))
print(f"录音文件: {path}")
import os
assert os.path.getsize(path) > 1000
print("录音测试通过")
```

**输入**: duration=5, sample_rate=16000
**输出**: WAV 文件路径，文件 < 5s 但 > 1KB
**验收**: 有文件生成，能播放出声音

---

#### Step A-4：测试 Whisper 转写（独立）

```python
import asyncio
from pipelines.audio.recorder import record_audio
from pipelines.audio.whisper_engine import transcribe

path = asyncio.run(record_audio(duration=5, sample_rate=16000))
result = await transcribe(path)
print(f"转写文本: {result['text']}")
print(f"Segments数: {len(result['segments'])}")
```

**输入**: WAV 文件路径
**输出**: {"text": "...", "segments": [...], "language": "zh"}
**验收**: text 不为空，segments 列表非空，每段有 start/end/confidence

---

#### Step A-5：测试流畅度分析

```python
from pipelines.audio.fluency_analyzer import analyze_fluency

segments = [
    {"text": "嗯我们就是这个项目", "start": 0.0, "end": 1.5, "confidence": 0.95},
    {"text": "就是说基于深度学习的", "start": 3.0, "end": 4.5, "confidence": 0.92},
    {"text": "我觉得效果还不错的", "start": 6.0, "end": 7.2, "confidence": 0.88},
    {"text": "然后然后我们测试了", "start": 9.0, "end": 10.5, "confidence": 0.90},
]
result = analyze_fluency(segments)

assert "avg_wpm" in result
assert "pause_count" in result
assert "filler_word_count" in result
assert "summary" in result
assert "score" in result
assert 0 <= result["score"] <= 100
print(f"WPM: {result['avg_wpm']}, 停顿: {result['pause_count']}, 评分: {result['score']}")

# 边界: 空输入不崩溃
empty = analyze_fluency([])
print("流畅度分析测试通过")
```

**输入**: segments 列表（带时间戳的文本片）
**输出**: FluencyReport 格式 dict
**验收**: 所有字段存在且类型正确，score 0-100，空输入不崩溃

---

#### Step A-6：测试 LLM 评审（独立）

```python
import asyncio
from models.session import BoothSession
from pipelines.llm.llm_engine import generate_review, FALLBACK_REVIEW

s = BoothSession()
s.transcript = "我们的项目是用AI做的一个智能垃圾分类系统"
s.fluency_report = {"avg_wpm": 150, "pause_count": 3, "filler_word_count": 2, "summary": "流畅度正常"}
s.emotion_report = {"tension_index": 0.3, "smile_index": 0.4, "overall_emotion": "relaxed_confident", "summary": "放松自信"}

review = await generate_review(s)
print(f"评审: {review}")

assert "insight" in review and len(review["insight"]) <= 25
assert "highlights" in review and 2 <= len(review["highlights"]) <= 3
assert "sharp_question" in review
assert "suggestions" in review and 1 <= len(review["suggestions"]) <= 2
assert "closing" in review

# 测试无 API Key 时的 fallback
import os
os.environ["LLM_API_KEY"] = ""
fallback = await generate_review(s)
assert fallback == FALLBACK_REVIEW  # 应返回占位评审
print("LLM 评审测试通过")
```

**输入**: session（含 transcript + fluency_report + emotion_report）
**输出**: ReviewReport 格式 dict
**验收**: 5 段字段全部存在，insight ≤ 25 字，API 不可用时返回 FALLBACK_REVIEW

---

#### Step A-7：测试 TTS（独立）

```python
from pipelines.tts.tts_engine import render_for_tts, synthesize_speech

review = {
    "insight": "选题不错，但工程深度不够。",
    "highlights": ["用了YOLOv8", "数据集做了标注"],
    "sharp_question": "你的模型在边缘设备上能跑吗？",
    "suggestions": ["做模型量化", "测试推理延迟"],
    "closing": "继续干，别停下来。",
}

text = render_for_tts(review)
print(f"TTS 文本: {text}")
assert "一句话" in text
assert "亮点" in text

import asyncio
path = asyncio.run(synthesize_speech(review))
print(f"音频文件: {path}")
import os
assert os.path.getsize(path) > 1000
print("TTS 测试通过")
```

**输入**: ReviewReport dict
**输出**: render_for_tts → 字符串；synthesize_speech → 音频文件路径
**验收**: 文本含 5 段关键词，音频 > 1KB

---

#### Step A-8：启动后端验证

```bash
cd D:/hks/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```
```bash
curl http://localhost:8000/api/health  # 预期: {"status":"ok"}
curl -X POST http://localhost:8000/api/step/welcome  # 预期: {"status":"ok","step":"presenting"}
```

### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| pyaudio 安装失败 | 缺 portaudio | Windows: pip install pipwin && pipwin install pyaudio |
| Whisper 连接失败 | Docker 没启动 | docker compose up -d |
| LLM API 超时 | 网络或 Key 不对 | 检查环境变量 LLM_API_KEY |
| Edge TTS 报错 | 首次需联网下载语音 | 等 10s 自动重试 |

---

## 调试任务 B：视觉管线

### 负责人：B

### 调试文件清单

| 文件 | 行数 | 功能 |
|------|------|------|
| backend/pipelines/video/camera.py | 103 | OpenCV 摄像头封装 |
| backend/pipelines/video/mediapipe_engine.py | 231 | FaceLandmarker 推理 |
| backend/pipelines/video/emotion_analyzer.py | 312 | 情绪指标提取 |
| backend/pipelines/video/processor.py | 103 | 视频管线编排入口 |
| backend/pipelines/output/photo_composer.py | 142 | 合影合成 |
| backend/pipelines/output/qr_generator.py | 74 | 二维码生成 |

### 你需要准备的环境

- ✅ Python 3.11+
- ✅ USB 摄像头（4K 或 1080p）
- ✅ 下载 MediaPipe 模型文件（见 Step B-3）
- ✅ 签名素材（可选）

### 测试步骤

#### Step B-1：验证依赖

```bash
cd D:/hks/backend && pip install -r requirements.txt
python -c "import cv2; print(f'OpenCV OK')"
python -c "import mediapipe; print(f'MediaPipe OK')"
```

#### Step B-2：测试摄像头

```python
import cv2
cap = cv2.VideoCapture(0)  # 如果 index 0 不行，试 1
assert cap.isOpened(), "摄像头无法打开"
ret, frame = cap.read()
assert ret, "无法读取帧"
print(f"分辨率: {frame.shape}")
cap.release()
print("摄像头测试通过")
```

**输入**: 无（打开默认摄像头）
**输出**: 一帧图像 (H, W, 3) numpy array
**验收**: cap.isOpened() = True，分辨率 >= 640x480

---

#### Step B-3：下载 MediaPipe 模型

```bash
cd D:/hks/backend
curl -L -o face_landmarker_v2.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
ls -la face_landmarker_v2.task  # 预期约 3.8MB
```

#### Step B-4：测试 FaceLandmarker

```python
import cv2
from pipelines.video.mediapipe_engine import FaceLandmarkerEngine

engine = FaceLandmarkerEngine()
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()
assert ret

result = engine.process_frame(frame, timestamp_ms=0)
print(f"人脸检测: {result['face_detected']}")
if result['face_detected']:
    print(f"关键点数: {len(result['landmarks'])}")    # 预期 478
    print(f"Blendshapes: {len(result['blendshapes'])}") # 预期 52
    print(f"头部姿态: {result['head_pose']}")
    assert len(result['landmarks']) == 478
    assert len(result['blendshapes']) == 52
print("FaceLandmarker 测试通过")
```

**输入**: 一帧图像
**输出**: face_detected + landmarks(478) + blendshapes(52) + head_pose
**验收**: 正对摄像头时 face_detected = True，landmarks=478，blendshapes=52

---

#### Step B-5：测试情绪提取

```python
from pipelines.video.emotion_analyzer import extract_emotion_signals

frame_features = []
for i in range(60):
    frame_features.append({
        "face_detected": True,
        "blendshapes": [
            {"category_name": "browInnerUp", "score": 0.3},
            {"category_name": "browOuterUp", "score": 0.2},
            {"category_name": "jawOpen", "score": 0.1},
            {"category_name": "mouthPress", "score": 0.2},
            {"category_name": "mouthSmileLeft", "score": 0.4},
            {"category_name": "mouthSmileRight", "score": 0.35},
            {"category_name": "eyeBlinkLeft", "score": 0.0},
            {"category_name": "eyeBlinkRight", "score": 0.0},
        ],
        "head_pose": {"yaw": 5, "pitch": 3, "roll": 1},
    })

emotion = extract_emotion_signals(frame_features)
assert 0 <= emotion["tension_index"] <= 1
assert 0 <= emotion["smile_index"] <= 1
assert emotion["overall_emotion"] in ["relaxed_confident", "slightly_nervous", "tense", "neutral"]
assert "summary" in emotion
print(f"紧张度: {emotion['tension_index']}, 总体情绪: {emotion['overall_emotion']}")

# 空输入测试
empty = extract_emotion_signals([{"face_detected": False, "blendshapes": [], "head_pose": {}}])
assert empty["signal_quality"] == "poor"
print("情绪提取测试通过")
```

**输入**: list[帧特征]
**输出**: EmotionReport 格式 dict
**验收**: 字段类型正确，空输入不崩溃，signal_quality 正确降级

---

#### Step B-6：测试合影 + QR

```python
from models.session import BoothSession
from pipelines.output.qr_generator import generate_qr
import asyncio

s = BoothSession()
s.review = {"insight": "测试", "highlights": [], "sharp_question": "", "suggestions": [], "closing": ""}
path = asyncio.run(generate_qr(s))
import os
assert os.path.getsize(path) > 100
print(f"QR 码生成: {path}")
print("输出模块测试通过")
```

**输入**: session（含 review）
**输出**: 二维码 PNG 文件路径
**验收**: 文件 > 100 bytes

### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 摄像头打不开 | index 不对 | 换 index: cap = cv2.VideoCapture(1) |
| MediaPipe 检测不到人脸 | 光线/距离 | 正面光源，距离 50-100cm |
| 模型文件找不到 | 没下载 | 运行 Step B-3 |

---

## 调试任务 C：前端 + TTS + H5

### 负责人：C

### 调试文件清单

| 文件 | 功能 |
|------|------|
| frontend/src/App.tsx | 主应用路由 |
| frontend/src/stores/boothStore.ts | Zustand 状态机 |
| frontend/src/hooks/useBoothSSE.ts | SSE 连接 |
| frontend/src/pages/Welcome.tsx | Step 1 |
| frontend/src/pages/Presenting.tsx | Step 2 |
| frontend/src/pages/Thinking.tsx | Step 3 |
| frontend/src/pages/Reviewing.tsx | Step 4 |
| frontend/src/pages/PhotoOutput.tsx | Step 5 |
| frontend/src/components/Countdown.tsx | 倒计时 |
| frontend/src/components/ReviewCard.tsx | 评审卡片 |
| frontend/src/components/QRDisplay.tsx | 二维码 |
| backend/pipelines/tts/tts_engine.py | Edge TTS |
| backend/pipelines/output/h5_generator.py | H5 评审页面 |

### 你的环境

- ✅ Node.js 18+
- ✅ 浏览器
- ❌ 不需要摄像头
- ❌ 不需要麦克风
- ❌ 不需要后端全功能（可用 mock 数据）

### 测试步骤

#### Step C-1：启动前端

```bash
cd D:/hks/frontend && npm install && npm run dev
```
打开 http://localhost:5173
**预期**: 黑底白字，显示"欢迎来到 X.AI 临时评审室"

#### Step C-2：验收 Welcome 页

- ☐ 显示欢迎语
- ☐ JetBrains Mono 等宽字体
- ☐ 纯黑背景 #000
- ☐ 倒计时组件显示 10s
- ☐ 10s 后调用 POST /api/step/welcome（Network tab 可看）

#### Step C-3：验收 Presenting 页（Mock SSE）

启动 mock SSE 服务：
```bash
cd D:/hks
python -c "
import asyncio, uvicorn, json
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

@app.get('/api/stream')
async def stream():
    async def gen():
        for step in ['welcome','presenting','thinking','reviewing','photo','complete']:
            yield f'event: message\ndata: {json.dumps({\"step\":step,\"countdown\":5,\"data\":{}},ensure_ascii=False)}\n\n'
            await asyncio.sleep(2)
        while True:
            await asyncio.sleep(30)
            yield f'event: message\ndata: {json.dumps({\"step\":\"complete\",\"countdown\":0,\"data\":{}},ensure_ascii=False)}\n\n'
    return Response(media_type='text/event-stream', content='')

@app.get('/api/health')
async def health(): return {'status':'ok'}
uvicorn.run(app, host='0.0.0.0', port=8000)
" &
```
验收页面按 2s 间隔自动切换 5 步。

#### Step C-4：验收 Reviewing 页样式

- ☐ 5 段评审卡片
- ☐ "一句话洞察" 大字突出
- ☐ 每个卡片入场动画
- ☐ "继续前往合影" 按钮

#### Step C-5：验收 PhotoOutput 页

- ☐ 合影照片显示
- ☐ 二维码显示
- ☐ "再来一次" 按钮刷新页面

#### Step C-6：测试 TTS（独立于前端）

```python
import asyncio
from pipelines.tts.tts_engine import synthesize_speech
review = {"insight":"选题不错。","highlights":["用了YOLOv8"],"sharp_question":"能跑多快？","suggestions":["量化"],"closing":"继续干。"}
path = asyncio.run(synthesize_speech(review))
import os; print(f"音频: {path}, 大小: {os.path.getsize(path)} bytes")
```

**验收**: 播放确认是中文男声

#### Step C-7：测试 H5 生成

```python
from pipelines.output.h5_generator import _build_html

review = {"insight":"选题不错","highlights":["YOLOv8","数据标注"],"sharp_question":"能跑多快？","suggestions":["量化"],"closing":"继续干"}
fluency = {"avg_wpm":150,"pause_count":3,"filler_word_count":2,"summary":"流畅度正常"}
emotion = {"tension_index":0.3,"smile_index":0.4,"overall_emotion":"relaxed_confident","summary":"放松自信"}

html = _build_html(review, fluency, emotion)
print(f"HTML: {len(html)} 字符")
with open("test_h5.html","w",encoding="utf-8") as f: f.write(html)
print("用浏览器打开 test_h5.html 确认样式")
```

**验收**: HTML 完整，5 段评审 + 流畅度/情绪数据显示，深色主题

### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| Vite 跨域 | proxy 配置 | 检查 vite.config.ts |
| SSE 不重连 | 浏览器限制 | useBoothSSE 有 3s 自动重连 |
| TTS 合成慢 | 首次下载语音 | 冷启动约 5-10s |

---

## 联合调试（三个人一起走一遍）

三个模块各自通过后，合在一起跑一次完整流程：

```
1. A 启动: docker compose up -d + uvicorn main:app
2. B 确认: 摄像头灯亮、麦克风灯亮
3. C 打开: http://localhost:5173 全屏
4. 一起走完 5 步（2min 路演 → 30s 思考 → 90s 评审 → 合影）
```

### 修复优先级

| 等级 | 问题类型 | 举例 |
|------|---------|------|
| P0 🔴 | 流程中断 | Step 2 到不了 Step 3 |
| P1 🟡 | 数据异常 | SSE 空推送 / 报告 fields 缺失 |
| P2 🟢 | 体验问题 | 动画卡 / 字体太小 / TTS 卡顿 |
| P3 🔵 | 视觉问题 | 样式偏差 / 布局偏移 |
