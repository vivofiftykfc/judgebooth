"""
H5 评审报告页面生成。

生成单页 HTML，包含项目信息、完整评审内容、合影图片、
流畅度+情绪雷达图数据、马斯克签名语录和分享按钮占位。
"""

import os
import json
import uuid
import logging

from backend.models.session import BoothSession

logger = logging.getLogger(__name__)

H5_OUTPUT_DIR = "D:/hks/backend/data/h5"


async def generate_h5(
    session: BoothSession,
    photo_path: str | None = None,
    output_dir: str = H5_OUTPUT_DIR,
) -> str:
    """
    生成评审报告的 H5 单页 HTML。

    包含:
    - 项目信息（名称 + 团队名）
    - 5 段完整评审
    - 合影图片
    - 流畅度 + 情绪雷达图数据
    - 马斯克签名语录
    - 分享按钮（占位）

    参数:
        session: BoothSession（含 review、fluency_report、emotion_report 等）
        photo_path: 合影图片路径（可选）
        output_dir: 输出目录

    返回:
        HTML 文件绝对路径
    """
    os.makedirs(output_dir, exist_ok=True)

    review = session.review or {}
    fluency = session.fluency_report or {}
    emotion = session.emotion_report or {}

    html = _build_html(
        review=review,
        fluency=fluency,
        emotion=emotion,
        photo_path=photo_path,
    )

    filename = f"review_{uuid.uuid4().hex[:8]}.html"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("H5 页面已生成: %s", output_path)
    return output_path


def _build_html(
    review: dict,
    fluency: dict,
    emotion: dict,
    photo_path: str | None = None,
) -> str:
    """构造单页 HTML 字符串。"""
    insight = review.get("insight", "")
    highlights = review.get("highlights", [])
    sharp_question = review.get("sharp_question", "")
    suggestions = review.get("suggestions", [])
    closing = review.get("closing", "")

    # 流畅度数据
    fluency_data = {
        "avg_wpm": fluency.get("avg_wpm", 0),
        "pause_count": fluency.get("pause_count", 0),
        "filler_word_count": fluency.get("filler_word_count", 0),
        "wpm_volatility": fluency.get("wpm_volatility", 0),
    }

    # 情绪数据
    emotion_data = {
        "tension_index": emotion.get("tension_index", 0),
        "smile_index": emotion.get("smile_index", 0),
        "gaze_at_camera_pct": emotion.get("gaze_at_camera_pct", 0),
        "head_stability_score": emotion.get("head_stability_score", 0),
    }

    highlights_html = "".join(
        f"<li>{h}</li>" for h in highlights
    ) if highlights else ""

    suggestions_html = "".join(
        f"<li>{s}</li>" for s in suggestions
    ) if suggestions else ""

    # 合影图片内联样式
    photo_html = ""
    if photo_path and os.path.exists(photo_path):
        photo_rel = os.path.basename(photo_path)
        photo_html = f'<div class="section"><h2>合影留念</h2><img src="../photos/{photo_rel}" alt="合影" style="width:100%;max-width:720px;border-radius:8px;border:1px solid #333;" /></div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>X.AI 评审报告</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'JetBrains Mono', 'PingFang SC', 'Microsoft YaHei', monospace;
      background: #000;
      color: #e0e0e0;
      max-width: 800px;
      margin: auto;
      padding: 20px;
      line-height: 1.8;
    }}
    h1 {{ color: #ffffff; font-size: 28px; margin-bottom: 8px; letter-spacing: 2px; }}
    .subtitle {{ color: #888; font-size: 14px; margin-bottom: 40px; }}
    .section {{
      margin: 30px 0;
      padding: 24px;
      border: 1px solid #333;
      border-radius: 12px;
      background: linear-gradient(135deg, #0a0a0a 0%, #111 100%);
    }}
    .section h2 {{ font-size: 18px; color: #aaa; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid #222; }}
    .quote {{
      font-style: italic;
      color: #ccc;
      border-left: 3px solid #e0e0e0;
      padding-left: 16px;
      font-size: 16px;
    }}
    ul {{ padding-left: 20px; }}
    li {{ margin: 8px 0; }}
    .button {{
      display: inline-block;
      margin: 20px 8px 0 0;
      padding: 12px 24px;
      background: transparent;
      color: #e0e0e0;
      border: 1px solid #555;
      border-radius: 8px;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.2s;
    }}
    .button:hover {{ background: #222; border-color: #888; }}
    .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .stat-item {{ padding: 12px; background: #0d0d0d; border-radius: 8px; }}
    .stat-label {{ color: #888; font-size: 12px; }}
    .stat-value {{ color: #fff; font-size: 20px; font-weight: bold; }}
    .footer {{ text-align: center; color: #555; font-size: 12px; margin: 60px 0 30px; }}
  </style>
</head>
<body>
  <h1>&#x26A1; X.AI 临时评审室</h1>
  <p class="subtitle">评审角色：埃隆·马斯克</p>

  <div class="section">
    <h2>&#x1F4AC; 一句话洞察</h2>
    <p class="quote">{_escape_html(insight)}</p>
  </div>

  <div class="section">
    <h2>&#x1F680; 硬核亮点</h2>
    <ul>{highlights_html}</ul>
  </div>

  <div class="section">
    <h2>&#x2753; 尖锐问题</h2>
    <p>{_escape_html(sharp_question)}</p>
  </div>

  <div class="section">
    <h2>&#x1F4A1; 硬核建议</h2>
    <ul>{suggestions_html}</ul>
  </div>

  <div class="section">
    <h2>&#x1F3C1; 结语</h2>
    <p class="quote">{_escape_html(closing)}</p>
  </div>

  {photo_html}

  <div class="section">
    <h2>&#x1F4CA; 路演表现数据</h2>
    <div class="stats">
      <div class="stat-item">
        <div class="stat-label">语速（词/分钟）</div>
        <div class="stat-value">{fluency_data["avg_wpm"]}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">停顿次数</div>
        <div class="stat-value">{fluency_data["pause_count"]}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">填充词次数</div>
        <div class="stat-value">{fluency_data["filler_word_count"]}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">语速波动率</div>
        <div class="stat-value">{fluency_data["wpm_volatility"]}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">紧张指数</div>
        <div class="stat-value">{emotion_data["tension_index"]}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">微笑指数</div>
        <div class="stat-value">{emotion_data["smile_index"]}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">注视镜头</div>
        <div class="stat-value">{emotion_data["gaze_at_camera_pct"]}%</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">头部稳定性</div>
        <div class="stat-value">{emotion_data["head_stability_score"]}</div>
      </div>
    </div>
  </div>

  <div>
    <button class="button" onclick="alert('分享功能即将上线')">&#x1F517; 分享报告</button>
    <button class="button" onclick="window.print()">&#x1F5A8; 打印 / PDF</button>
  </div>

  <div class="footer">
    <p>Generated by X.AI Review Booth &mdash; Hackathon Legends</p>
  </div>

  <script>
    // 雷达图数据（Chart.js 预留）
    const fluencyData = {json.dumps(fluency_data, ensure_ascii=False)};
    const emotionData = {json.dumps(emotion_data, ensure_ascii=False)};
  </script>
</body>
</html>"""


def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符。"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
