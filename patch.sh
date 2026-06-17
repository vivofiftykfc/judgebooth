#!/usr/bin/env bash
# 补丁管理脚本
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

case "${1:-help}" in
  status)
    echo "=== 补丁状态 ==="
    for f in "$ROOT/patches"/*.patch; do
      [ -f "$f" ] || continue
      name=$(basename "$f" .patch)
      if git -C "$ROOT" apply --check "$f" 2>/dev/null; then
        echo "  [待应用] $name"
      else
        echo "  [已应用] $name"
      fi
    done
    ;;
  apply)
    target="${2:-}"
    for f in "$ROOT/patches"/*.patch; do
      [ -f "$f" ] || continue
      name=$(basename "$f" .patch)
      [ -n "$target" ] && [[ "$name" != "$target"* ]] && continue
      if git -C "$ROOT" apply --check "$f" 2>/dev/null; then
        git -C "$ROOT" apply "$f"
        echo "  ✅ 已应用: $name"
      else
        echo "  ⏭️  已跳过（可能已应用）: $name"
      fi
    done
    ;;
  rollback)
    if git -C "$ROOT" log --oneline -1 2>/dev/null | grep -q "patch"; then
      git -C "$ROOT" reset --soft HEAD~1
      echo "✅ 已回滚"
    else
      echo "没有找到可回滚的提交"
    fi
    ;;
  *)
    echo "用法: bash patch.sh <status|apply|rollback>"
    echo "  status    查看补丁状态"
    echo "  apply     应用所有补丁"
    echo "  apply 001 应用指定补丁"
    echo "  rollback  回滚"
    ;;
esac
