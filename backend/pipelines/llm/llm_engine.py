"""
LLM API 调用封装。

调用 Anthropic 风格的消息 API 生成评审报告，
包含重试、解析验证和 fallback 机制。
"""

import json
import os
import logging
import re

import httpx

from models.session import BoothSession
from pipelines.llm.prompt_builder import build_prompt

logger = logging.getLogger(__name__)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv(
    "LLM_API_URL", "https://api.anthropic.com/v1/messages"
)
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")


# fallback 评审（当 LLM 不可用时）
FALLBACK_REVIEW: dict = {
    "insight": "项目有想法，但需要更深度的工程验证。",
    "highlights": ["选题方向有潜力", "团队有执行力"],
    "sharp_question": "如果去掉所有现有工具，从零开始你会怎么做？",
    "suggestions": ["做一个最小可行原型验证核心假设", "关注物理可行性而非流行技术"],
    "closing": "继续干，别停下来。",
}


async def generate_review(session: BoothSession) -> dict:
    """
    调用 LLM API 生成评审报告。

    逻辑:
    1. 调用 prompt_builder.build_prompt(session) 获取消息
    2. POST 到 LLM_API_URL
    3. 从响应中解析 JSON
    4. 验证包含 insight, highlights, sharp_question, suggestions, closing
    5. 不满足则重试（最多 2 次）
    6. 返回 review dict

    错误处理:
    - API 调用失败 → session.error 记录，返回 fallback 评审
    - 解析失败 → 尝试从文本中提取 JSON
    - 全部失败 → 返回硬编码的占位评审
    """
    messages = build_prompt(session)

    last_error: Exception | None = None
    for attempt in range(3):  # 初始调用 + 最多 2 次重试
        try:
            response_data = await _call_llm_api(messages)
            review = await _parse_review_response(response_data)

            if _validate_review(review):
                return review

            logger.warning(
                "LLM 响应验证失败（attempt %d/3），重试中...", attempt + 1
            )
        except Exception as exc:
            last_error = exc
            logger.error(
                "LLM API 调用异常（attempt %d/3）: %s", attempt + 1, exc
            )

    # 所有尝试失败，记录错误并使用 fallback
    error_msg = (
        f"LLM 评审生成失败: {last_error}" if last_error else "LLM 响应验证不通过"
    )
    session.error = error_msg
    logger.error("使用 fallback 评审: %s", error_msg)
    return dict(FALLBACK_REVIEW)


async def _call_llm_api(messages: list) -> str:
    """
    实际的 HTTP 调用，带超时和重试。

    参数:
        messages: 多轮对话消息列表

    返回:
        LLM 响应的文本内容

    抛出:
        httpx.HTTPError: 网络/HTTP 错误
        ValueError: 响应格式异常
    """
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY 未设置，无法调用 LLM API")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": LLM_API_KEY,
        "anthropic-version": "2023-06-01",
    }

    body = {
        "model": LLM_MODEL,
        "max_tokens": 1024,
        "messages": messages,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(LLM_API_URL, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()

    # 解析 Anthropic 消息格式
    content_blocks = data.get("content", [])
    for block in content_blocks:
        if block.get("type") == "text":
            return block.get("text", "")

    raise ValueError("LLM 响应中没有 text 类型的内容块")


async def _parse_review_response(response_text: str) -> dict:
    """
    从 LLM 响应中提取并验证 JSON。

    策略:
    1. 尝试直接解析整个响应为 JSON
    2. 尝试从 markdown 代码块中提取 JSON（```json ... ```）
    3. 尝试用正则查找最外层的 JSON 对象
    """
    # 策略 1: 整体解析
    text = response_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 策略 2: 提取 markdown 代码块
    code_block_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL
    )
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 策略 3: 正则查找最外层 JSON 对象
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("无法从 LLM 响应中解析 JSON")


def _validate_review(review: dict) -> bool:
    """
    验证 review dict 包含所有必要字段。

    必要字段: insight, highlights, sharp_question, suggestions, closing
    highlights 和 suggestions 必须是列表类型。
    """
    required_fields = ["insight", "highlights", "sharp_question", "suggestions", "closing"]
    for field in required_fields:
        if field not in review:
            logger.warning("review 缺少必要字段: %s", field)
            return False

    if not isinstance(review.get("highlights"), list):
        logger.warning("review.highlights 不是列表")
        return False

    if not isinstance(review.get("suggestions"), list):
        logger.warning("review.suggestions 不是列表")
        return False

    return True
