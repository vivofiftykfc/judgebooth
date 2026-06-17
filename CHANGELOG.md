# 变更日志

## 2026-06-18 调试会话

### [修复] 录音停不下来
- **原因**: PyAudio 阻塞模式导致 stop_recording 无效
- **修复**: 改用回调模式 (`stream_callback`)
- **涉及**: `backend/pipelines/audio/recorder.py`

### [修复] Thinking 页面卡死
- **原因**: 三管线完成后没推进 step
- **修复**: 自动 `session.step = "reviewing"`
- **涉及**: `backend/services/pipeline_orchestrator.py`

### [修复] 合影/二维码不显示
- **原因**: Vite 没配 `/static` proxy + 路径没转 URL
- **修复**: 加 proxy + 静态挂载 + `_path_to_url()`
- **涉及**: `frontend/vite.config.ts`, `backend/main.py`, `backend/models/session.py`

### [修复] End Early 按钮不响应
- **原因**: `useCallback` 闭包 + 没做乐观更新
- **修复**: 改为普通函数 + fetch 后立即跳转
- **涉及**: `frontend/src/pages/Presenting.tsx`

### [修复] session_id 不存在
- **涉及**: `backend/models/session.py`

### [修复] 录音录两遍
- **涉及**: `backend/pipelines/audio/processor.py`

### [修复] 摄像头和浏览器抢资源
- **涉及**: `backend/pipelines/video/processor.py`, `frontend/src/pages/Presenting.tsx`

### [新增] 调试日志系统
- **涉及**: `backend/debug_utils.py`, `DEBUG_TUTORIAL.md`

### [修复] 自动结束任务误触
- **涉及**: `backend/main.py`
