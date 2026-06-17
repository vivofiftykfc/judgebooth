"""
二维码生成模块。

为评审报告生成二维码，扫码后跳转到 H5 评审报告页面。
"""

import os
import uuid
import logging

import qrcode

from models.session import BoothSession

logger = logging.getLogger(__name__)

QR_OUTPUT_DIR = "D:/hks/backend/data/qr"


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
    os.makedirs(QR_OUTPUT_DIR, exist_ok=True)

    h5_url = await _resolve_h5_url(session)
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

    logger.info("二维码已生成: %s -> %s", output_path, h5_url)
    return output_path


async def _resolve_h5_url(session: BoothSession) -> str:
    """
    解析 H5 页面的 URL。

    当前版本返回本地路径占位。
    未来版本应上传到静态托管并返回完整 URL。
    """
    return _upload_h5(session.review or {}, session)


async def _upload_h5(review: dict, session: BoothSession) -> str:
    """
    上传 H5 到静态托管，返回 URL。

    当前版本返回本地路径占位。
    """
    return f"/h5/{session.session_id}.html"
