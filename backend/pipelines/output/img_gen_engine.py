"""
AI 生图引擎 — InfiniteYou 换脸方案

用你的模板图 + InfiniteYou 把你的脸换上去
"""

import asyncio
import io
import os
import time
import uuid
import logging

import httpx
from PIL import Image, ImageDraw, ImageFont

from debug_utils import print_debug, print_step, print_data, print_error, print_file_size

logger = logging.getLogger(__name__)

API_KEY = os.getenv("IMG_GEN_API_KEY", "")
API_BASE = "https://api.wavespeed.ai/api/v3"

# Polaroid 模板图路径
TEMPLATE_PATH = "D:/hks/backend/assets/polaroid_template.png"


async def generate_portrait_card(
    reference_image_path: str,
    prompt: str = "",
    review: dict | None = None,
    qr_path: str | None = None,
    output_dir: str = "D:/hks/backend/data/photos",
) -> str | None:
    """InfiniteYou 换脸：模板图 + 你的脸"""
    if not API_KEY or not os.path.isfile(reference_image_path):
        return None

    print_step("IMG_GEN", "=== InfiniteYou 换脸 ===")
    t0 = time.time()

    try:
        public_host = os.getenv("PUBLIC_HOST", "http://localhost:8000")

        # 模板图 URL（你的 Polaroid 卡模板，从 static 目录服务）
        template_url = f"{public_host.rstrip('/')}/static/photos/polaroid_template.png"
        if not os.path.isfile(TEMPLATE_PATH) and not os.path.isfile("D:/hks/backend/data/photos/polaroid_template.png"):
            print_error("IMG_GEN", "模板图不存在")
            return None
        print_debug("IMG_GEN", f"模板 URL: {template_url}")

        # 你的脸 URL（摄像头拍的照片）
        face_url = f"{public_host.rstrip('/')}/static/photos/{os.path.basename(reference_image_path)}"
        print_debug("IMG_GEN", f"人脸 URL: {face_url}")

        # 调用 InfiniteYou 换脸
        result_url = await _call_infinite_you(face_url, template_url)
        if not result_url:
            print_error("IMG_GEN", "InfiniteYou 换脸失败")
            return None

        # 下载结果
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"card_{uuid.uuid4().hex[:8]}.jpg")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(result_url)
            resp.raise_for_status()
            img_data = resp.content

        # Pillow：右下角贴二维码（缩小）
        img = Image.open(io.BytesIO(img_data)).convert("RGB")
        w, h = img.size
        draw = ImageDraw.Draw(img)

        if qr_path and os.path.isfile(qr_path):
            try:
                qr = Image.open(qr_path).convert("RGBA")
                qr_size = min(w, h) // 6  # 缩小到卡片的 1/6
                qr = qr.resize((qr_size, qr_size), Image.LANCZOS)
                margin = int(w * 0.04)
                qr_x = w - qr_size - margin
                qr_y = h - qr_size - margin
                # 半透明白底
                draw.rounded_rectangle([qr_x - 6, qr_y - 6, qr_x + qr_size + 6, qr_y + qr_size + 6],
                                      radius=6, fill=(255, 255, 255, 200))
                img.paste(qr, (qr_x, qr_y), qr)
                print_debug("IMG_GEN", f"二维码已贴右下角: {qr_size}px")
            except Exception as e:
                print_debug("IMG_GEN", f"二维码粘贴失败: {e}")

        img.save(out_path, quality=95)
        elapsed = time.time() - t0
        print_file_size("IMG_GEN", out_path)
        print_step("IMG_GEN", f"InfiniteYou 换脸完成，耗时 {elapsed:.1f}s")
        return out_path

    except Exception as e:
        print_error("IMG_GEN", f"失败: {e}")
        return None


async def _call_infinite_you(source_url: str, target_url: str) -> str | None:
    """InfiniteYou 换脸：source=你的脸, target=模板图"""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    body = {"source_image": source_url, "target_image": target_url, "seed": 42}
    url = f"{API_BASE}/wavespeed-ai/infinite-you"
    print_debug("IMG_GEN", "InfiniteYou 换脸...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            print_error("IMG_GEN", f"API 错误: {e.response.status_code} {e.response.text[:300]}")
            return None
        except httpx.ConnectError:
            print_error("IMG_GEN", "无法连接 WaveSpeedAI")
            return None

    pid = data.get("data", {}).get("id")
    if not pid:
        print_error("IMG_GEN", f"无 prediction_id: {data}")
        return None

    poll_url = f"{API_BASE}/predictions/{pid}/result"
    for _ in range(60):
        await asyncio.sleep(2)
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                pr = await client.get(poll_url, headers=headers)
                pr.raise_for_status()
                pd = pr.json()
            except Exception:
                continue
        status = pd.get("data", {}).get("status")
        if status == "completed":
            outputs = pd.get("data", {}).get("outputs", [])
            if outputs:
                url = outputs[0] if isinstance(outputs, list) else outputs
                print_debug("IMG_GEN", f"换脸完成: {url}")
                return url
        elif status == "failed":
            err = pd.get("data", {}).get("error", "?")
            print_error("IMG_GEN", f"换脸失败: {err}")
            return None

    print_error("IMG_GEN", "轮询超时")
    return None
