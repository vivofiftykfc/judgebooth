# 语音识别升级：本地 Whisper → Soniox 实时转写

> 把语音输入从本地 faster-whisper(small) 换成 **Soniox 云端实时转写(stt-rt-v5)**。
> 浏览器端流式 + **实时字幕**，结束时把最终文本 + 词级时间戳交给后端做流畅度/评审。

---

## 为什么换
旧的本地 whisper small 实测问题：音近字错（语音→运营、黑客松→黑客送）、中英混说强制 zh 会乱、
还有后端 pyaudio 录音的**双录/超时 bug**（录到 101.5s）。

Soniox 一次全解决：
- 云端大模型，准确率明显更高
- `languageHints: ['zh','en']`，**中英混说**也能对
- **实时字幕**：边说边出字（Presenting 页 "Live Transcript"）
- **不再用后端录音** → 双录/超时 bug 直接没了

---

## 架构
```
浏览器麦克风 ──stream──> Soniox WebSocket (stt-rt-v5)
   │  用后端签发的 60s 临时 key 连（真 key 不进前端）
   │  <── 实时 token(interim+final) ──┘  → Presenting 实时字幕
   └─ 结束时：最终文本 + 词级 token  POST 给后端
                                        → 后端用它算流畅度 + 喂 LLM 评审
```

---

## 改了哪些文件（zip 里已按目录放好，覆盖即可）

**后端**
| 文件 | 改动 |
|------|------|
| `backend/config.py` | 新增 `SONIOX_API_KEY` / `SONIOX_TEMP_KEY_URL` / `SONIOX_ENABLED` |
| `backend/main.py` | 新增 `POST /api/soniox/temp-key`（签发临时 key）、`POST /api/step/presenting/transcript`（接收前端转写）；presenting/start **不再触发后端录音**（除非没配 Soniox）；welcome 重置 transcript_segments |
| `backend/models/session.py` | 新增字段 `transcript_segments`（词级 token 转的 segments） |
| `backend/pipelines/audio/processor.py` | 有 Soniox 转写时**跳过录音+whisper**，直接用它算流畅度；没配 Soniox 时仍走旧录音兜底 |

**前端**
| 文件 | 改动 |
|------|------|
| `frontend/src/hooks/useSoniox.ts` | **新增**：Soniox 客户端 hook（接流 / 累积 final+interim / start/stop） |
| `frontend/src/pages/Presenting.tsx` | 接入 useSoniox：开始起流、加"Live Transcript"实时字幕、结束时把文本发后端 |
| `frontend/package.json` | + `@soniox/speech-to-text-web` |

---

## 怎么启用（两步）

```bash
# 1) 后端：设环境变量（真 key 只放这里，前端用临时 key）
set SONIOX_API_KEY=674207a2fc777a5e2ced9de69f561e65db7741e0f2563a926afa028b08cbc1bb

# 2) 前端：装 SDK
cd frontend && npm install @soniox/speech-to-text-web@1.4.0
npm run build   # 应 0 报错
```

启动后端时连同之前的变量一起：
```
set KMP_DUPLICATE_LIB_OK=TRUE
set LLM_API_KEY=sk-...
set SONIOX_API_KEY=674207...
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 注意
- **要联网**（Soniox 是云服务）。没配 `SONIOX_API_KEY` 时自动回退到旧的本地 whisper（兜底）。
- 临时 key 端点用真 key 换 60s 临时 key 返给前端 → **真 key 不暴露在浏览器**。
- 实测已通：实时字幕正常、转写明显更准（中英混说也对）、后端不再录音。
- 注意 Soniox 返回 **201** 才是成功（不是 200），代码已按 `>= 300` 判失败。

> 另：Photo 页的两个 bug（`tw` 变量未赋值 / 输出模块 `D:/hks` 硬编码致 404）我也在本地修了，
> 那是另一块，需要的话单独发你。
