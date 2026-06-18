import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from config import (
    AUDIO_DURATION,
    CAMERA_INDEX,
    SONIOX_API_KEY,
    SONIOX_TEMP_KEY_URL,
    SONIOX_ENABLED,
)
from models.session import BoothSession
from services.pipeline_orchestrator import PipelineOrchestrator
from debug_utils import print_debug, print_step, print_data, print_error

# ---------------------------------------------------------------------------
# Global state (single-session, in-process singleton)
# ---------------------------------------------------------------------------
session = BoothSession()
sse_queues: list[asyncio.Queue] = []
_auto_end_task: asyncio.Task | None = None  # 自动结束任务，welcome/reset 时取消


async def broadcast_state() -> None:
    """Push current session state into every connected SSE queue."""
    data = session.to_sse()
    dead: list[asyncio.Queue] = []
    for q in sse_queues:
        try:
            await q.put(data)
        except Exception:
            dead.append(q)
    for q in dead:
        try:
            sse_queues.remove(q)
        except ValueError:
            pass


async def _notify() -> None:
    await broadcast_state()


orchestrator = PipelineOrchestrator(session, notify=_notify)


# ---------------------------------------------------------------------------
# Lifespan — camera init on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup: attempt camera init. Shutdown: log."""
    print_step("MAIN", "=== 服务启动 ===")
    print(f"Initialising camera at index {CAMERA_INDEX}...")
    try:
        import cv2

        cap = cv2.VideoCapture(CAMERA_INDEX)
        if cap.isOpened():
            print("Camera opened successfully.")
        else:
            print("Camera not available (will be retried at recording time).")
        cap.release()
    except ImportError:
        print("cv2 not installed — camera init deferred.")
    except Exception as exc:
        print(f"Camera init warning: {exc}")
    yield
    print_step("MAIN", "=== 服务关闭 ===")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(title="Legendary Review Booth", lifespan=lifespan)

# 挂载静态文件目录，供前端访问合影和二维码
import os
_static_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(os.path.join(_static_dir, "photos"), exist_ok=True)
os.makedirs(os.path.join(_static_dir, "qr"), exist_ok=True)
os.makedirs(os.path.join(_static_dir, "h5"), exist_ok=True)
os.makedirs(os.path.join(_static_dir, "audio"), exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require_step(expected: str) -> None:
    """Guard: raise 409 if current step is not the expected one."""
    if session.step != expected:
        raise HTTPException(
            status_code=409,
            detail=f"Current step is '{session.step}', expected '{expected}'",
        )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    print_debug("MAIN", "健康检查 GET /api/health")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Soniox 临时密钥（前端用它建立 WebSocket，真 key 不暴露给浏览器）
# ---------------------------------------------------------------------------
@app.post("/api/soniox/temp-key")
async def soniox_temp_key():
    """用后端的 SONIOX_API_KEY 换一个 60s 临时 key 返给前端。"""
    if not SONIOX_ENABLED:
        raise HTTPException(status_code=503, detail="SONIOX_API_KEY 未配置")
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                SONIOX_TEMP_KEY_URL,
                headers={"Authorization": f"Bearer {SONIOX_API_KEY}"},
                json={"usage_type": "transcribe_websocket", "expires_in_seconds": 60},
            )
        if resp.status_code >= 300:
            print_error("SONIOX", f"临时 key 获取失败: {resp.status_code} {resp.text[:200]}")
            raise HTTPException(status_code=502, detail="Soniox 临时密钥获取失败")
        data = resp.json()
        # 兼容字段名：api_key
        api_key = data.get("api_key") or data.get("apiKey")
        print_debug("SONIOX", "已签发临时 key")
        return {"apiKey": api_key, "expiresAt": data.get("expires_at")}
    except HTTPException:
        raise
    except Exception as e:
        print_error("SONIOX", f"临时 key 异常: {e}")
        raise HTTPException(status_code=502, detail=f"Soniox 临时密钥异常: {e}")


# ---------------------------------------------------------------------------
# SSE stream
# ---------------------------------------------------------------------------
@app.get("/api/stream")
async def stream(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    sse_queues.append(queue)
    print_debug("MAIN", f"SSE 客户端连接，当前队列数: {len(sse_queues)}")

    async def event_generator():
        try:
            # Send current state immediately on connect
            data = session.to_sse()
            print_debug("MAIN", f"SSE 发送初始状态: step={data.get('step')}")
            yield {
                "event": "message",
                "data": json.dumps(data, ensure_ascii=False),
            }

            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    step = data.get("step") if isinstance(data, dict) else "?"
                    print_debug("MAIN", f"SSE 推送状态: step={step}")
                    yield {
                        "event": "message",
                        "data": json.dumps(data, ensure_ascii=False),
                    }
                except asyncio.TimeoutError:
                    # Heartbeat — re-send current state to keep connection alive
                    yield {
                        "event": "message",
                        "data": json.dumps(session.to_sse(), ensure_ascii=False),
                    }
        except asyncio.CancelledError:
            print_debug("MAIN", "SSE 连接被取消")
        finally:
            try:
                sse_queues.remove(queue)
                print_debug("MAIN", f"SSE 客户端断开，剩余队列: {len(sse_queues)}")
            except ValueError:
                pass

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# 5-step state machine
# ---------------------------------------------------------------------------

@app.post("/api/step/welcome")
async def step_welcome():
    """Reset session, set 10s countdown, move to presenting."""
    global _auto_end_task
    print_step("MAIN", "=== Step: welcome ===")
    print_debug("MAIN", "重置会话，设置 10s 倒计时")

    # 取消上一个自动结束任务（防止旧任务在新 session 中误触发）
    if _auto_end_task and not _auto_end_task.done():
        _auto_end_task.cancel()
        print_debug("MAIN", "已取消旧的自动结束任务")
        _auto_end_task = None

    session.step = "welcome"
    session.countdown = 10
    session.audio_path = None
    session.transcript = None
    session.transcript_segments = None
    session.fluency_report = None
    session.emotion_report = None
    session.review = None
    session.review_audio_path = None
    session.photo_path = None
    session.qr_path = None
    session.error = None
    session.video_frames = None
    session.camera_instance = None
    session.step = "presenting"
    await broadcast_state()
    print_debug("MAIN", f"welcome 完成，当前 step={session.step}")
    return {"status": "ok", "step": session.step}


@app.post("/api/step/presenting/frame")
async def step_presenting_frame(request: Request):
    """接收前端传来的视频帧（Base64 JPEG），存入 session.video_frames。"""
    if session.step != "presenting":
        return {"status": "ignored", "reason": "not in presenting step"}
    try:
        body = await request.json()
        frame_data = body.get("frame", "")
        if not frame_data:
            return {"status": "error", "reason": "no frame data"}
        # 确保列表已初始化
        if session.video_frames is None:
            session.video_frames = []
        # 存到列表（只存最近 600 帧 ≈ 120s @ 5fps）
        if len(session.video_frames) < 600:
            session.video_frames.append(frame_data)
        return {"status": "ok", "stored": len(session.video_frames)}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


@app.post("/api/step/presenting/transcript")
async def step_presenting_transcript(request: Request):
    """接收前端 Soniox 实时转写的最终文本 + 词级 token，存入 session。

    body: {"text": str, "tokens": [{"text","start_ms","end_ms","is_final"}, ...]}
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    text = (body.get("text") or "").strip()
    tokens = body.get("tokens") or []

    # 词级 token → fluency_analyzer 用的 segments（start/end 单位：秒）
    segments = []
    for t in tokens:
        s = t.get("start_ms")
        e = t.get("end_ms")
        segments.append({
            "text": t.get("text", ""),
            "start": (s / 1000.0) if s is not None else 0.0,
            "end": (e / 1000.0) if e is not None else 0.0,
            "confidence": 1.0,
        })

    session.transcript = text
    session.transcript_segments = segments
    print_data("MAIN", "前端 Soniox 转写文本", text)
    print_debug("MAIN", f"收到 Soniox 转写: {len(text)} 字, {len(tokens)} tokens")
    return {"status": "ok", "len": len(text), "tokens": len(tokens)}


@app.post("/api/step/presenting/start")
async def step_presenting_start():
    """Start 120 s recording (audio + video pipelines)."""
    global _auto_end_task
    print_step("MAIN", "=== Step: presenting/start ===")
    _require_step("presenting")
    session.countdown = AUDIO_DURATION
    print_debug("MAIN", f"开始录制，倒计时={AUDIO_DURATION}s")
    await broadcast_state()

    # 语音由前端 Soniox 实时转写（不再用后端 pyaudio 录音）。
    # 仅当 Soniox 未配置时，留作离线兜底由音频管线在分析阶段自行录制。
    if not SONIOX_ENABLED:
        asyncio.create_task(orchestrator.start_recording())

    # Auto-end（保存引用，welcome 或 end 时取消）
    async def _auto_end():
        await asyncio.sleep(AUDIO_DURATION)
        if session.step == "presenting":
            print_debug("MAIN", "自动结束录制（超时）")
            try:
                await step_presenting_end()
            except Exception as e:
                print_error("MAIN", f"自动结束录制异常: {e}")

    _auto_end_task = asyncio.create_task(_auto_end())

    return {"status": "ok", "step": session.step}


@app.post("/api/step/presenting/end")
async def step_presenting_end():
    """Stop recording, enter thinking state, start 3-pipeline analysis."""
    global _auto_end_task
    print_step("MAIN", "=== Step: presenting/end ===")

    # 如果已经是 thinking（自动结束已触发），直接返回成功
    if session.step != "presenting":
        print_debug("MAIN", f"step 已经是 {session.step}，跳过（可能自动结束已触发）")
        return {"status": "ok", "step": session.step}
    session.step = "thinking"
    session.countdown = 0

    # 取消自动结束任务（用户手动结束了，不让 auto_end 再触发一次）
    if _auto_end_task and not _auto_end_task.done():
        _auto_end_task.cancel()
        _auto_end_task = None
        print_debug("MAIN", "已取消自动结束任务（用户手动结束）")

    print_debug("MAIN", "进入思考阶段，启动三管线分析")
    await broadcast_state()

    # Analysis runs in background — it pushes progress via SSE
    asyncio.create_task(orchestrator.analyze())

    return {"status": "ok", "step": session.step}


@app.post("/api/step/thinking/complete")
async def step_thinking_complete():
    """Analysis done — move to reviewing."""
    print_step("MAIN", "=== Step: thinking/complete ===")
    _require_step("thinking")
    print_data("MAIN", "session.transcript", session.transcript)
    print_data("MAIN", "session.fluency_report", session.fluency_report)
    print_data("MAIN", "session.emotion_report", session.emotion_report)
    print_data("MAIN", "session.review", session.review)
    print_data("MAIN", "session.error", session.error)
    session.step = "reviewing"
    await broadcast_state()
    return {"status": "ok", "step": session.step}


@app.post("/api/step/reviewing/complete")
async def step_reviewing_complete():
    """Review acknowledged — move to photo state and start output generation."""
    print_step("MAIN", "=== Step: reviewing/complete ===")
    _require_step("reviewing")
    session.step = "photo"
    print_debug("MAIN", "进入合影阶段，启动输出生成")
    await broadcast_state()

    # Generate photo + QR code in background
    asyncio.create_task(orchestrator.generate_output())

    return {"status": "ok", "step": session.step}


@app.post("/api/step/photo/complete")
async def step_photo_complete():
    """Photo taken — session complete."""
    print_step("MAIN", "=== Step: photo/complete ===")
    _require_step("photo")
    session.step = "complete"
    print_debug("MAIN", f"会话完成，photo_path={session.photo_path}, qr_path={session.qr_path}")
    await broadcast_state()
    return {"status": "ok", "step": session.step}
