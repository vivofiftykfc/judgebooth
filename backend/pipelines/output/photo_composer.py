"""
合影合成模块。

流程:
  1. 尝试 AI 生图引擎
  2. 失败 → Pillow 合成赛博朋克风格 Polaroid 纪念卡
"""

import os
import uuid
import logging
import time
import math

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from debug_utils import print_debug, print_step, print_data, print_error, print_file_size

logger = logging.getLogger(__name__)

# 卡片参数（3:4 竖版）
W = 1200
H = 1600
PHOTO_MARGIN = 50
PHOTO_BOX = (PHOTO_MARGIN, 230, W - PHOTO_MARGIN, 1050)  # 照片区

# 配色
BLACK = (8, 8, 16)
DARK_BLUE = (12, 18, 48)
CARD_BG = (16, 22, 56)
NEON_CYAN = (0, 230, 255)
NEON_PURPLE = (160, 80, 255)
NEON_ORANGE = (255, 180, 50)
WHITE = (240, 240, 245)
GRAY = (140, 140, 160)
DIM_WHITE = (200, 200, 210)


async def compose_photo(
    camera_best_photo_path: str | None = None,
    review: dict | None = None,
    qr_path: str | None = None,
    output_dir: str = "D:/hks/backend/data/photos",
) -> str:
    """合成合影。"""
    print_step("PHOTO", "=== 合影合成 ===")
    os.makedirs(output_dir, exist_ok=True)
    t0 = time.time()

    # 兼容 session 对象
    session = None
    if hasattr(camera_best_photo_path, 'photo_path'):
        session = camera_best_photo_path
        camera_best_photo_path = session.photo_path
        if review is None and session:
            review = session.review
        if qr_path is None and session:
            qr_path = session.qr_path

    # ---- AI 生图 ----
    if camera_best_photo_path and os.path.isfile(camera_best_photo_path) and os.getenv("IMG_GEN_API_KEY"):
        print_debug("PHOTO", "尝试 AI 生图...")
        try:
            from pipelines.output.img_gen_engine import generate_portrait_card
            ai_path = await generate_portrait_card(camera_best_photo_path, review=review, qr_path=qr_path, output_dir=output_dir)
            if ai_path and os.path.isfile(ai_path):
                elapsed = time.time() - t0
                print_step("PHOTO", f"AI 卡完成，耗时 {elapsed:.1f}s")
                return ai_path
        except Exception as e:
            print_error("PHOTO", f"AI 失败: {e}")

    # ---- Pillow 合成 ----
    print_step("PHOTO", ">> Pillow 合成赛博 Polaroid")
    card = Image.new("RGB", (W, H), DARK_BLUE)
    draw = ImageDraw.Draw(card)

    # 1. 背景渐变效果（逐条渐变线）
    for y in range(H):
        ratio = y / H
        r = int(DARK_BLUE[0] * (1 - ratio) + 8 * ratio)
        g = int(DARK_BLUE[1] * (1 - ratio) + 10 * ratio)
        b = int(DARK_BLUE[2] * (1 - ratio) + 30 * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 2. 科技网格（半透明线条）
    grid_color = (30, 50, 100, 80)
    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill=(20, 35, 70), width=1)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=(20, 35, 70), width=1)

    # 3. 卡片主体（深色半透明 Polaroid 白卡效果的变体）
    card_w = W - 60
    card_h = H - 60
    card_x = 30
    card_y = 30
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h],
                          radius=24, fill=(20, 28, 68), outline=(40, 60, 120), width=2)

    # 4. 内发光边框
    glow_rect = [card_x + 8, card_y + 8, card_x + card_w - 8, card_y + card_h - 8]
    draw.rounded_rectangle(glow_rect, radius=18, outline=(30, 50, 110), width=1)

    # 5. 顶部霓虹标题栏
    title_bar_y = card_y + 20
    draw.rounded_rectangle([card_x + 20, title_bar_y, card_x + card_w - 20, title_bar_y + 60],
                          radius=8, fill=(25, 35, 80), outline=NEON_CYAN, width=1)

    title_font = _font(48, bold=True)
    draw.text((W // 2, title_bar_y + 30), "传 奇 评 审 亭",
              fill=NEON_CYAN, font=title_font, anchor="mm")

    # 6. 照片区（带霓虹边框）
    px1, py1, px2, py2 = PHOTO_BOX
    photo_bg_rect = [px1 - 4, py1 - 4, px2 + 4, py2 + 4]
    draw.rounded_rectangle(photo_bg_rect, radius=12, fill=(10, 15, 35),
                          outline=NEON_PURPLE, width=2)

    # 插入照片
    has_photo = False
    if camera_best_photo_path and os.path.isfile(camera_best_photo_path):
        try:
            photo = Image.open(camera_best_photo_path).convert("RGB")
            pw, ph = photo.size
            tw = px2 - px1
            th = py2 - py1
            scale = max(tw / pw, th / ph)
            nw = int(pw * scale)
            nh = int(ph * scale)
            photo = photo.resize((nw, nh), Image.LANCZOS)
            left = (nw - tw) // 2
            top = (nh - th) // 2
            photo = photo.crop((left, top, left + tw, top + th))
            card.paste(photo, (px1, py1))
            has_photo = True
        except Exception as e:
            print_error("PHOTO", f"照片嵌入失败: {e}")

    if not has_photo:
        draw.text((px1 + tw // 2, py1 + th // 2), "◉ PHOTO",
                  fill=DIM_WHITE, font=_font(48), anchor="mm")

    # 7. 底部信息区
    info_y = py2 + 30

    # 语录（用 AI 评审的结语）
    closing = (review or {}).get("closing", "") or "继续干，别停下来"
    qf = _font(34)
    draw.text((W // 2, info_y), f"「{closing}」", fill=WHITE, font=qf, anchor="mm")

    # 分隔装饰线
    line_y = info_y + 55
    draw.line([(W // 2 - 200, line_y), (W // 2 + 200, line_y)],
             fill=NEON_CYAN, width=1)
    draw.line([(W // 2 - 190, line_y + 3), (W // 2 + 190, line_y + 3)],
             fill=(30, 50, 110), width=1)

    # 签名
    sig_y = line_y + 35
    sig_font = _font(26)
    draw.text((W - 80, sig_y), "— AI评委：马斯克", fill=GRAY, font=sig_font, anchor="rt")

    # 8. 二维码（左下角）
    if qr_path and os.path.isfile(qr_path):
        try:
            qr_img = Image.open(qr_path).convert("RGBA")
            qr_size = 130
            qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
            # 白底半透明
            qr_bg_x = card_x + 25
            qr_bg_y = sig_y + 40
            draw.rounded_rectangle([qr_bg_x - 8, qr_bg_y - 8,
                                    qr_bg_x + qr_size + 8, qr_bg_y + qr_size + 8],
                                  radius=8, fill=(20, 28, 68), outline=NEON_CYAN, width=1)
            card.paste(qr_img, (qr_bg_x, qr_bg_y), qr_img)
        except Exception as e:
            print_debug("PHOTO", f"二维码嵌入失败: {e}")

    # 9. 认证章（右下角）
    stamp_text = "AI评审认证"
    sf = _font(18)
    sb = draw.textbbox((0, 0), stamp_text, font=sf)
    sw = sb[2] - sb[0] + 24
    sh = sb[3] - sb[1] + 14
    sx = W - 40 - sw
    sy = sig_y + 55
    draw.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=10,
                          outline=NEON_ORANGE, width=2)
    draw.text((sx + 12, sy + 7), stamp_text, fill=NEON_ORANGE, font=sf)

    # 10. 角落装饰
    corners = [
        (card_x + 10, card_y + 10, card_x + 30, card_y + 10),
        (card_x + card_w - 10, card_y + 10, card_x + card_w - 30, card_y + 10),
        (card_x + 10, card_y + card_h - 10, card_x + 30, card_y + card_h - 10),
        (card_x + card_w - 10, card_y + card_h - 10, card_x + card_w - 30, card_y + card_h - 10),
    ]
    for i, (x1, y1, x2, y2) in enumerate(corners):
        if i < 2:
            draw.line([(x1, y1), (x2, y2)], fill=NEON_CYAN, width=2)
        else:
            draw.line([(x1, y1), (x2, y2)], fill=NEON_PURPLE, width=2)

    # 保存
    filename = f"polaroid_{uuid.uuid4().hex[:8]}.jpg"
    output_path = os.path.join(output_dir, filename)
    card.save(output_path, quality=95)

    elapsed = time.time() - t0
    print_file_size("PHOTO", output_path)
    print_step("PHOTO", f"赛博 Polaroid 完成，耗时 {elapsed:.1f}s")
    return output_path


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    fonts = [
        ("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc", size),
        ("C:/Windows/Fonts/simhei.ttf", size),
        ("C:/Windows/Fonts/simsun.ttc", size),
    ]
    for path, sz in fonts:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, sz)
            except Exception:
                continue
    return ImageFont.load_default()
