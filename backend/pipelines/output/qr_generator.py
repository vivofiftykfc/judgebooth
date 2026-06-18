"""
二维码生成模块。

为评审报告生成二维码，扫码后跳转到 H5 评审报告页面。
"""

import os
import uuid
import logging
import time

import qrcode

from models.session import BoothSession
from debug_utils import print_debug, print_step, print_data, print_error, print_file_size

logger = logging.getLogger(__name__)

QR_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "qr")


async def generate_qr(session: BoothSession) -> str:
    """
    生成评审报告的二维码。

    逻辑:
    1. 构建评审 H5 的 URL
    2. 使用 qrcode 库生成二维码
    3. 保存到 QR_OUTPUT_DIR
    4. 返回文件路径

    参数:
        session: BoothSession（含 review、session_id）

    返回:
        二维码图片文件绝对路径
    """
    print_step("QR", "=== 二维码生成 ===")
    os.makedirs(QR_OUTPUT_DIR, exist_ok=True)

    t0 = time.time()
    h5_url = await _resolve_h5_url(session)
    print_debug("QR", f"H5 URL: {h5_url}")

    filename = f"qr_{uuid.uuid4().hex[:8]}.png"
    output_path = os.path.join(QR_OUTPUT_DIR, filename)

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(h5_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)

    elapsed = time.time() - t0
    print_file_size("QR", output_path)
    print_step("QR", f"二维码生成完成，耗时 {elapsed:.1f}s")
    return output_path


async def _resolve_h5_url(session: BoothSession) -> str:
    """生成 H5 页面的完整 URL（用公网地址，手机才能扫码访问）。"""
    public_host = os.getenv("PUBLIC_HOST", "http://localhost:8000")
    return f"{public_host.rstrip('/')}/static/h5/review_{session.session_id}.html"


async def _upload_h5(review: dict, session: BoothSession) -> str:
    """
    上传 H5 到静态托管，返回 URL。

    当前版本返回静态文件 URL（H5 由 generate_h5 生成到 data/h5/）。
    """
    return f"/static/h5/review_{session.session_id}.html"
