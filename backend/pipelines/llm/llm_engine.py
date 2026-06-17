"""
LLM API 调用封装。

调用 OpenAI 兼容格式的消息 API（支持 DeepSeek、OpenAI 等）生成评审报告，
包含重试、解析验证和 fallback 机制。
"""

import json
import os
import logging
import re

import httpx

from models.session import BoothSession
from pipelines.llm.prompt_builder import build_prompt
from debug_utils import print_debug, print_step, print_data, print_error

logger = logging.getLogger(__name__)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv(
    "LLM_API_URL", "https://api.deepseek.com/v1/chat/completions"
)
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")


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
    2. POST 到 LLM_API_URL（OpenAI 兼容格式）
    3. 从响应中解析 JSON
    4. 验证包含 insight, highlights, sharp_question, suggestions, closing
    5. 不满足则重试（最多 2 次）
    6. 返回 review dict
    """
    print_step("LLM", "=== 评审生成 ===")
    messages = build_prompt(session)

    # 检查 API Key
    if not LLM_API_KEY:
        print_error("LLM", "LLM_API_KEY 未设置，使用 fallback 评审")
        session.error = "LLM_API_KEY 未设置"
        return dict(FALLBACK_REVIEW)

    print_debug("LLM", f"API URL: {LLM_API_URL}")
    print_debug("LLM", f"Model: {LLM_MODEL}")
    print_data("LLM", "system 消息长度", len(messages[0].get("content", "")))
    print_data("LLM", "user 消息长度", len(messages[1].get("content", "")))

    last_error: Exception | None = None
    for attempt in range(3):
        print_step("LLM", f">> API 调用第 {attempt+1}/3 次尝试")
        try:
            import time
            t0 = time.time()
            response_data = await _call_llm_api(messages)
            elapsed = time.time() - t0
            print_debug("LLM", f"API 响应完成，耗时 {elapsed:.1f}s")
            print_data("LLM", "原始响应（前200字符）", response_data[:200])

            review = await _parse_review_response(response_data)
            if _validate_review(review):
                print_step("LLM", "评审 JSON 验证通过")
                print_data("LLM", "生成的 insight", review.get("insight", ""))
                return review

            logger.warning("LLM 响应验证失败（attempt %d/3），重试中...", attempt + 1)
            print_error("LLM", f"响应验证失败（attempt {attempt+1}/3）")
        except Exception as exc:
            last_error = exc
            logger.error("LLM API 调用异常（attempt %d/3）: %s", attempt + 1, exc)
            print_error("LLM", f"API 调用异常: {exc}")

    error_msg = (
        f"LLM 评审生成失败: {last_error}" if last_error else "LLM 响应验证不通过"
    )
    session.error = error_msg
    logger.error("使用 fallback 评审: %s", error_msg)
    print_error("LLM", f"使用 fallback 评审: {error_msg}")
    print_data("LLM", "fallback_review", FALLBACK_REVIEW)
    return dict(FALLBACK_REVIEW)


async def _call_llm_api(messages: list) -> str:
    """
    OpenAI 兼容格式的 HTTP 调用。

    参数:
        messages: 多轮对话消息列表

    返回:
        LLM 响应的文本内容
    """
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY 未设置，无法调用 LLM API")

    # 截断 API Key 用于 debug 显示
    key_preview = LLM_API_KEY[:8] + "..." if len(LLM_API_KEY) > 8 else "?"
    print_debug("LLM", f"使用 API Key: {key_preview}")
    print_debug("LLM", f"请求 URL: {LLM_API_URL}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }

    body = {
        "model": LLM_MODEL,
        "max_tokens": 1024,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }

    import time
    t0 = time.time()
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(LLM_API_URL, headers=headers, json=body)
        elapsed = time.time() - t0
        print_debug("LLM", f"HTTP 响应: status={response.status_code}, 耗时 {elapsed:.1f}s")
        response.raise_for_status()
        data = response.json()

    # 解析 OpenAI 兼容格式
    choices = data.get("choices", [])
    if not choices:
        raise ValueError("LLM 响应中没有 choices")

    finish_reason = choices[0].get("finish_reason", "?")
    usage = data.get("usage", {})
    print_debug("LLM", f"finish_reason={finish_reason}, usage={usage}")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("LLM 响应中 message.content 为空")

    print_debug("LLM", f"响应内容长度: {len(content)} 字符")
    return content


async def _parse_review_response(response_text: str) -> dict:
    """
    从 LLM 响应中提取并验证 JSON。

    策略:
    1. 尝试直接解析整个响应为 JSON
    2. 尝试从 markdown 代码块中提取 JSON（```json ... ```）
    3. 尝试用正则查找最外层的 JSON 对象
    """
    text = response_text.strip()

    # 策略 1: 整体解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 策略 2: 提取 markdown 代码块
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
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
    """验证 review dict 包含所有必要字段。"""
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
