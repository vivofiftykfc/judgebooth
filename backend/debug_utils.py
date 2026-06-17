"""
调试工具模块 — 提供统一的调试打印接口。

所有模块用此模块的 print_debug / print_step / print_data / print_error
替代裸 print，保证格式统一，且可通过 DEBUG_MODE 一键开关。
"""

import datetime
import os
import sys

# 是否开启调试输出（默认打开，可在 config.py 中统一关闭）
DEBUG_MODE = os.getenv("DEBUG", "1") == "1"


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:12]


def print_debug(tag: str, msg: str):
    """常规调试信息。"""
    if not DEBUG_MODE:
        return
    print(f"  [DEBUG][{_timestamp()}][{tag}] {msg}", flush=True)


def print_step(tag: str, msg: str):
    """步骤级信息 — 用 >>> 突出显示。"""
    if not DEBUG_MODE:
        return
    print(f"\n  >>> [STEP][{_timestamp()}][{tag}] {msg}", flush=True)


def print_data(tag: str, label: str, data):
    """打印关键数据（自动处理 None/空/长度）。"""
    if not DEBUG_MODE:
        return
    if data is None:
        print(f"  [DATA][{_timestamp()}][{tag}] {label} = <None>", flush=True)
    elif isinstance(data, str):
        snippet = data[:120].replace("\n", "\\n")
        print(f"  [DATA][{_timestamp()}][{tag}] {label} = '{snippet}' (len={len(data)})", flush=True)
    elif isinstance(data, list):
        print(f"  [DATA][{_timestamp()}][{tag}] {label} = [{len(data)} items]", flush=True)
    elif isinstance(data, dict):
        print(f"  [DATA][{_timestamp()}][{tag}] {label} = {{{len(data)} keys}} {list(data.keys())}", flush=True)
    else:
        print(f"  [DATA][{_timestamp()}][{tag}] {label} = {data}", flush=True)


def print_error(tag: str, msg: str):
    """错误信息 — 用 !!! 突出。"""
    if not DEBUG_MODE:
        return
    print(f"  >>> !!! [ERROR][{_timestamp()}][{tag}] {msg}", flush=True)


def print_file_size(tag: str, path: str):
    """打印文件大小。"""
    if not DEBUG_MODE:
        return
    try:
        size = os.path.getsize(path)
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / 1024 / 1024:.1f} MB"
        print(f"  [DEBUG][{_timestamp()}][{tag}] 文件: {path} ({size_str})", flush=True)
    except OSError:
        print(f"  [DEBUG][{_timestamp()}][{tag}] 文件不存在: {path}", flush=True)
