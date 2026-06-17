# 传奇评审亭 — Loop Runbook

> **Pattern**: sequential
> **Mode**: safe
> **Stop Condition**: Wave 4.5 complete (quality-gate + security-reviewer pass)

---

## Wave 0：骨架搭建

**执行者**: 我
**操作**:
1. `mkdir -p` 全部目录结构
2. 写 `docker-compose.yml`
3. 写 `backend/requirements.txt`
4. 写 `frontend/package.json` + Vite + Tailwind + TypeScript configs
5. 写 `CLAUDE.md`
6. 写所有 `__init__.py`
7. Commit

**验收**: 目录结构完整，`git status` 干净

---

## Wave 1A：FastAPI 主应用

**执行者**: Agent A
**文件**: `backend/main.py` + `config.py` + `models/*.py` + `services/*.py`
**验收**: `uvicorn backend.main:app` 启动成功，`GET /health` → 200

---

## Wave 1B：音频管线（与 1A 并行）

**执行者**: Agent B
**文件**: `backend/pipelines/audio/recorder.py` + `whisper_engine.py` + `fluency_analyzer.py`
**验收**: 传入 WAV 返回转写文本 + 流畅度指标

---

## Wave 1.5：审查

**技能**: `ecc:code-review`
**重点**: SSE 格式、Whisper 超时重试、数据模型一致性

---

## Wave 2C：视频管线

**执行者**: Agent C
**文件**: `backend/pipelines/video/camera.py` + `mediapipe_engine.py` + `emotion_analyzer.py`
**验收**: 给帧返回 478 关键点 + 情绪指标

---

## Wave 2D：LLM + TTS + 输出（与 2C 并行）

**执行者**: Agent D
**文件**: `backend/pipelines/llm/*.py` + `tts/*.py` + `output/*.py`
**验收**: 给定文本返回评审 + 音频 + 合影

---

## Wave 2.5：审查

**技能**: `ecc:code-review`
**重点**: 降级处理、LLM 重试、TTS 缓存

---

## Wave 3：前端

**执行者**: Agent E
**文件**: `frontend/src/**/*`
**验收**: `npm run dev` 启动，5 页面可切换

---

## Wave 3.5：审查

**技能**: `ecc:code-review` + `typescript-reviewer`
**重点**: SSE 类型对齐、倒计时精确性、动画过渡

---

## Wave 4：联调

**执行者**: 我
**操作**: docker-compose up → uvicorn → npm run dev → 走 5 步流程

---

## Wave 4.5：最终检查

**技能**: `ecc:quality-gate` + `security-reviewer`
**验收**: 全部通过
**Stop Condition Met** ✅
