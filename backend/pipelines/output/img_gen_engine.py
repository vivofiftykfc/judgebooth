"""
AI 生图引擎 — 阿里云 Wan2.7-Image

多图参考：模板 Polaroid 卡 + 你的照片 → 换头（脸+头发完整替换）
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
API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
MODEL = "wan2.7-image-pro"

PROMPT = (
    "将第二张照片中的人物完整提取出来，以第一张图的艺术风格重新绘制后，"
    "替换掉第一张图右侧区域的人。保持第一张图的卡片设计、背景、文字布局完全不变。"
    "人物的面部、头发、以及包括衣服、外套、配饰在内的全部穿着打扮，均与第二张照片完全一致。"
)


async def generate_portrait_card(
    reference_image_path: str,
    prompt: str = PROMPT,
    review: dict | None = None,
    qr_path: str | None = None,
    output_dir: str = "D:/hks/backend/data/photos",
) -> str | None:
    """Wan2.7 换头：模板 Polaroid 卡 + 你的照片"""
    if not API_KEY or not os.path.isfile(reference_image_path):
        return None

    print_step("IMG_GEN", "=== Wan2.7-Image 换头 ===")
    t0 = time.time()

    try:
        public_host = os.getenv("PUBLIC_HOST", "http://localhost:8000")

        # 两张图：模板卡 + 你的照片
        template_url = f"{public_host.rstrip('/')}/static/photos/polaroid_template.png"
        face_url = f"{public_host.rstrip('/')}/static/photos/{os.path.basename(reference_image_path)}"

        if not os.path.isfile("D:/hks/backend/data/photos/polaroid_template.png"):
            print_error("IMG_GEN", "模板图不存在")
            return None

        # 读取模板尺寸，保持输出比例一致
        tmpl = Image.open("D:/hks/backend/data/photos/polaroid_template.png")
        out_size = f"{tmpl.width}*{tmpl.height}"
        print_debug("IMG_GEN", f"输出尺寸: {out_size}")

        # 调用 API
        result_data = await _call_wan(template_url, face_url, out_size)
        if not result_data:
            return None

        # 下载结果
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"card_{uuid.uuid4().hex[:8]}.jpg")
        with open(out_path, "wb") as f:
            f.write(result_data)

        # Pillow 叠二维码（右下角）
        img = Image.open(out_path).convert("RGB")
        w, h = img.size
        draw = ImageDraw.Draw(img)

        if qr_path and os.path.isfile(qr_path):
            try:
                qr = Image.open(qr_path).convert("RGBA")
                qs = min(w, h) // 6
                qr = qr.resize((qs, qs), Image.LANCZOS)
                m = int(w * 0.04)
                draw.rounded_rectangle([m - 6, h - qs - m - 6, m + qs + 6, h - m + 6],
                                      radius=6, fill=(255, 255, 255, 200))
                img.paste(qr, (m, h - qs - m), qr)
            except Exception as e:
                print_debug("IMG_GEN", f"二维码粘贴失败: {e}")

        img.save(out_path, quality=95)
        elapsed = time.time() - t0
        print_file_size("IMG_GEN", out_path)
        print_step("IMG_GEN", f"Wan2.7 换头完成，耗时 {elapsed:.1f}s")
        return out_path

    except Exception as e:
        print_error("IMG_GEN", f"失败: {e}")
        return None


async def _call_wan(template_url: str, face_url: str, size: str = "1K") -> bytes | None:
    """调用 Wan2.7-Image 多图编辑"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    body = {
        "model": MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": template_url},
                        {"image": face_url},
                        {"text": PROMPT},
                    ],
                }
            ]
        },
        "parameters": {
            "size": size,
            "n": 1,
            "watermark": False,
        },
    }

    print_debug("IMG_GEN", "调用 Wan2.7-Image...")

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            resp = await client.post(API_URL, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            print_error("IMG_GEN", f"API 错误: {e.response.status_code} {e.response.text[:300]}")
            return None
        except httpx.ConnectError:
            print_error("IMG_GEN", "无法连接阿里云 API")
            return None

    # 解析响应，取图片 URL
    try:
        choices = data.get("output", {}).get("choices", [])
        if not choices:
            print_error("IMG_GEN", f"响应无 choices: {data}")
            return None
        content = choices[0].get("message", {}).get("content", [])
        if not content:
            print_error("IMG_GEN", "响应无 content")
            return None
        img_url = content[0].get("image", "")
        if not img_url:
            print_error("IMG_GEN", "响应无 image URL")
            return None

        print_debug("IMG_GEN", f"生成完成: {img_url}")

        # 下载
        async with httpx.AsyncClient(timeout=120.0) as client:
            img_resp = await client.get(img_url)
            img_resp.raise_for_status()
            return img_resp.content

    except (KeyError, IndexError) as e:
        print_error("IMG_GEN", f"响应解析失败: {data}")
        return None
