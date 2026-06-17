import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from config import AUDIO_DURATION, CAMERA_INDEX
from models.session import BoothSession
from services.pipeline_orchestrator import PipelineOrchestrator

# ---------------------------------------------------------------------------
# Global state (single-session, in-process singleton)
# ---------------------------------------------------------------------------
session = BoothSession()
sse_queues: list[asyncio.Queue] = []


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
    print("Backend shutting down.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(title="Legendary Review Booth", lifespan=lifespan)

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
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# SSE stream
# ---------------------------------------------------------------------------
@app.get("/api/stream")
async def stream(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    sse_queues.append(queue)

    async def event_generator():
        try:
            # Send current state immediately on connect
            yield {
                "event": "message",
                "data": json.dumps(session.to_sse(), ensure_ascii=False),
            }

            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
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
            pass
        finally:
            try:
                sse_queues.remove(queue)
            except ValueError:
                pass

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# 5-step state machine
# ---------------------------------------------------------------------------

@app.post("/api/step/welcome")
async def step_welcome():
    """Reset session, set 10s countdown, move to presenting."""
    session.step = "welcome"
    session.countdown = 10
    session.audio_path = None
    session.transcript = None
    session.fluency_report = None
    session.emotion_report = None
    session.review = None
    session.photo_path = None
    session.qr_path = None
    session.error = None
    session.step = "presenting"
    await broadcast_state()
    return {"status": "ok", "step": session.step}


@app.post("/api/step/presenting/start")
async def step_presenting_start():
    """Start 120 s recording (audio + video pipelines)."""
    _require_step("presenting")
    session.countdown = AUDIO_DURATION
    await broadcast_state()

    # Start recording in background
    asyncio.create_task(orchestrator.start_recording())

    # Auto-end after the max duration
    async def _auto_end():
        await asyncio.sleep(AUDIO_DURATION)
        if session.step == "presenting":
            try:
                await step_presenting_end()
            except Exception:
                pass

    asyncio.create_task(_auto_end())

    return {"status": "ok", "step": session.step}


@app.post("/api/step/presenting/end")
async def step_presenting_end():
    """Stop recording, enter thinking state, start 3-pipeline analysis."""
    _require_step("presenting")
    session.step = "thinking"
    session.countdown = 0
    await broadcast_state()

    # Analysis runs in background — it pushes progress via SSE
    asyncio.create_task(orchestrator.analyze())

    return {"status": "ok", "step": session.step}


@app.post("/api/step/thinking/complete")
async def step_thinking_complete():
    """Analysis done — move to reviewing."""
    _require_step("thinking")
    session.step = "reviewing"
    await broadcast_state()
    return {"status": "ok", "step": session.step}


@app.post("/api/step/reviewing/complete")
async def step_reviewing_complete():
    """Review acknowledged — move to photo state and start output generation."""
    _require_step("reviewing")
    session.step = "photo"
    await broadcast_state()

    # Generate photo + QR code in background
    asyncio.create_task(orchestrator.generate_output())

    return {"status": "ok", "step": session.step}


@app.post("/api/step/photo/complete")
async def step_photo_complete():
    """Photo taken — session complete."""
    _require_step("photo")
    session.step = "complete"
    await broadcast_state()
    return {"status": "ok", "step": session.step}
