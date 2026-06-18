# 马斯克朗读（Edge TTS）

> 评审就绪后，把评审报告渲染成一段**连贯的口语独白**（不是机械念卡片），
> 中文走厚实男声、穿插的英文句走低沉英文男声，合成一条 mp3，
> 在 Reviewing 页**自动播放**——"马斯克当面宣判"。

---

## ⚠️ 应用顺序（重要）
本包的 `session.py` 和 `main.py` 是**在 Soniox 那一版基础上叠加**的（含 Soniox 的改动）。
所以：**先应用 Soniox 包，再应用本 TTS 包**（本包的这两个文件会覆盖成"同时含 Soniox + TTS"的完整版）。
其余文件互不冲突。

---

## 效果
- 进 Reviewing 页**自动播放**马斯克点评（被浏览器拦截自动播时，有"▶ 听马斯克点评"按钮 + 声波动画）。
- 脚本是**连贯独白 + 英文穿插**（开场/转折/结尾用英文，最容易让人听出是马斯克）：
  ```
  [英文] "Alright. Let me be brutally honest with you."
  [中文] 你这个项目，{洞察}……我承认有几个地方还行，{亮点}……
  [英文] "But here's the real question."
  [中文] {尖锐问题}……想让它真的成，你得这么干，{建议}……{结语}
  [英文] "Make it work, or don't bother. Keep going."
  ```
- 声音设置（在 `tts_engine.py` 顶部，可调）：
  - 中文：`zh-CN-YunjianNeural`（厚实）+ 降调 `-12Hz`（深沉）
  - 英文：`en-US-ChristopherNeural`（低沉）+ 微降 `-3Hz`
  - 语速：`+8%`（干脆）

---

## 改了哪些文件（zip 已按目录放好）

**后端**
| 文件 | 改动 |
|------|------|
| `backend/pipelines/tts/tts_engine.py` | 重写：`build_musk_script`(连贯脚本) + `synthesize_musk_speech`(中英分声、逐段重试、拼接成一条 mp3)；输出目录改相对路径 |
| `backend/services/pipeline_orchestrator.py` | 三管线跑完、进 reviewing 前，调 TTS 生成朗读音频 → `session.review_audio_path`（失败降级不阻断） |
| `backend/models/session.py` | 新增 `review_audio_path` 字段 + `to_sse` 暴露 `review_audio`（含 Soniox 改动） |
| `backend/main.py` | welcome 重置 `review_audio_path`（含 Soniox 改动） |

**前端**
| 文件 | 改动 |
|------|------|
| `frontend/src/pages/Reviewing.tsx` | 新增 `<audio>` 自动播放 + 播放/暂停按钮 + 声波动画 |
| `frontend/src/stores/boothStore.ts` | data 类型加 `review_audio` 字段 |

---

## 依赖 / 集成
- **无新依赖**：`edge_tts` 你们已经在用。
- 朗读音频在**分析阶段后台生成**（评审就绪后、进 reviewing 前），所以进 Reviewing 时音频已就位，延迟藏在"思考"里。
- 生成的 mp3 落在 `backend/data/audio/`，经 `/static/audio/...` 提供给前端。
- 想调声音/语速/脚本：改 `tts_engine.py` 顶部常量 + `build_musk_script`。

> 真·马斯克音色（RVC 换声）在这台机器上 pip 装不上（依赖地狱），暂用 Edge TTS。
> 真音色后续走 RVC 一键整合包再补。
