"""
合影合成模块。

将摄像头最佳帧与马斯克签名 PNG、活动 Logo PNG 叠加，
生成带有评审结语的合影照片。
"""

import os
import uuid
import logging

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# 素材路径
SIGNATURE_PATH = "D:/hks/backend/assets/musk_signature.png"
LOGO_PATH = "D:/hks/backend/assets/event_logo.png"

# 输出参数
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
SIGNATURE_SIZE = (300, 100)
LOGO_SIZE = (200, 80)

# 结语文字位置和样式
CLOSING_POSITION = (960, 1000)  # 底部居中
CLOSING_FONT_SIZE = 36
CLOSING_COLOR = (255, 255, 255)


async def compose_photo(
    camera_best_photo_path: str | None = None,
    review: dict | None = None,
    output_dir: str = "D:/hks/backend/data/photos",
) -> str:
    """
    合成合影。

    逻辑:
    1. 加载摄像头最佳帧（如果为 None 则创建占位图）
    2. 用 Pillow 叠加马斯克签名 PNG
    3. 叠加活动 Logo PNG
    4. 底部叠加一句结语
    5. 保存到 output_dir
    6. 返回路径

    参数:
        camera_best_photo_path: 摄像头最佳帧路径（可选，None 时创建占位图）
        review: 评审报告 dict（含 closing 字段，可选）
        output_dir: 输出目录

    返回:
        合成后的合影文件绝对路径
    """
    os.makedirs(output_dir, exist_ok=True)

    if camera_best_photo_path and os.path.isfile(camera_best_photo_path):
        try:
            img = Image.open(camera_best_photo_path).convert("RGB")
        except Exception:
            img = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (30, 30, 30))
    else:
        logger.warning("摄像头最佳帧不存在，创建纯色占位图")
        img = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (30, 30, 30))

    # 调整尺寸到标准输出
    img = img.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.LANCZOS)

    # 叠加签名
    img = _overlay_signature(img, SIGNATURE_PATH)

    # 叠加 Logo
    img = _overlay_logo(img, LOGO_PATH)

    # 叠加结语
    closing_text = review.get("closing", "") if review else ""
    if closing_text:
        img = _overlay_closing_text(img, closing_text)

    filename = f"photo_{uuid.uuid4().hex[:8]}.jpg"
    output_path = os.path.join(output_dir, filename)
    img.save(output_path, quality=95)

    logger.info("合影已合成: %s", output_path)
    return output_path


def _overlay_signature(
    img: Image.Image,
    signature_path: str = SIGNATURE_PATH,
) -> Image.Image:
    """右下角叠加马斯克签名 PNG。"""
    try:
        sig = Image.open(signature_path).convert("RGBA")
        sig = sig.resize(SIGNATURE_SIZE, Image.LANCZOS)
        # 右下角，留边距 50px
        position = (OUTPUT_WIDTH - SIGNATURE_SIZE[0] - 50, 50)
        img = img.copy()
        img.paste(sig, position, sig)
    except FileNotFoundError:
        logger.info("签名素材不存在，跳过: %s", signature_path)
    return img


def _overlay_logo(
    img: Image.Image,
    logo_path: str = LOGO_PATH,
) -> Image.Image:
    """左上角叠加活动 Logo PNG。"""
    try:
        logo = Image.open(logo_path).convert("RGBA")
        logo = logo.resize(LOGO_SIZE, Image.LANCZOS)
        position = (50, 50)
        img = img.copy()
        img.paste(logo, position, logo)
    except FileNotFoundError:
        logger.info("Logo 素材不存在，跳过: %s", logo_path)
    return img


def _overlay_closing_text(img: Image.Image, text: str) -> Image.Image:
    """底部居中叠加结语文字。"""
    draw = ImageDraw.Draw(img)

    # 尝试加载字体，失败则用默认
    try:
        font = ImageFont.truetype(
            "C:/Windows/Fonts/msyh.ttc", CLOSING_FONT_SIZE
        )
    except (IOError, OSError):
        font = ImageFont.load_default()

    # 获取文字尺寸
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (OUTPUT_WIDTH - text_width) // 2
    y = CLOSING_POSITION[1]

    # 黑色阴影底边提升可读性
    shadow_offset = 2
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0))
    draw.text((x, y), text, font=font, fill=CLOSING_COLOR)

    return img
