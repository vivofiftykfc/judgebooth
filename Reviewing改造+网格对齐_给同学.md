# Reviewing 页改造 + 人脸网格对齐（前端）

> TTS 之后做的两块，**纯前端**：
> ① Reviewing 页套控制台主题 + 加"你的表现"数据面板；② 修人脸网格绿点错位。

---

## ⚠️ 应用顺序（重要）
本包的 4 个文件是**叠加了之前所有改动的最新版**（含 UI / Soniox / TTS 的相关改动）。
**请在 UI 包、Soniox 包、TTS 包都应用之后，最后再应用本包**——这 4 个文件会覆盖成最终完整版。
本包**只有前端、无后端改动**（TTS 的后端在 TTS 包里，已就位）。

---

## ① Reviewing 页改造
- 套上**控制台 HUD 主题**（黑底 / X 红 / Anton 字体），和前 3 页统一；标题"他的**判决**"。
- 马斯克朗读控件融进主题（▶ 听他说 + 声波动画）。
- **新增"你的表现"数据面板**（之前算了但完全没展示的多模态数据）：
  - 综合状态（自信放松/紧张…，按情绪上色）
  - 进度条：看镜头% / 头部稳定 / 微笑度 / 紧张度
  - 数字：语速(字/分) / 停顿次数 / 口头禅次数 + 一句话概述
- **颜色按数值梯度**：≥66 绿、≥33 琥珀、否则红；紧张度对齐分类阈值（<0.3 绿 / 0.3–0.6 琥珀 / ≥0.6 红）。
- 去掉了对 `ReviewCard` 组件的依赖（改内联 HUD 卡片）。

## ② 人脸网格绿点对齐修复
之前 canvas 内部分辨率用的是**显示框尺寸**，而视频是 `object-cover`（裁剪），坐标系对不上 → 绿点偏移。
修复：canvas 内部分辨率改用**摄像头原生分辨率**，canvas 也加 `object-cover`，与视频裁剪一致 → 自动贴合人脸。

---

## 改了哪些文件（zip 已按目录放好，覆盖即可）
```
frontend/src/pages/Reviewing.tsx        # 改造：主题 + 表现面板（含 TTS 朗读控件，是最新版）
frontend/src/stores/boothStore.ts       # data 类型补全 fluency/emotion 字段（含 review_audio）
frontend/src/hooks/useFaceMesh.ts        # 网格对齐：用原生分辨率
frontend/src/pages/Presenting.tsx        # 叠加网格 canvas 的 object-cover（含 UI/Soniox 改动，是最新版）
```

## 集成
- **无新依赖**。覆盖文件后 `cd frontend && npm run build`（应 0 报错）。
- "你的表现"数据是后端 SSE 已经在传的 `data.fluency` / `data.emotion`，前端只是显示出来。

> 备注：紧张度 `tension_index` 指标本身偏低、区分度弱（blendshape 加权和难到 0.6），
> 颜色我已对齐分类阈值；若想让它更灵敏，需另外重标定 `emotion_analyzer` 的紧张度公式。
