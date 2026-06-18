@echo off
chcp 65001 >nul
echo ============================================
echo   JudgeBooth - 传奇评审亭 环境安装脚本
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [^!] Python 未安装，请先安装 Python 3.10+
    echo     下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python 已就绪

:: 检查 Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [^!] Node.js 未安装，请先安装 Node.js 18+
    echo     下载: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js 已就绪

echo.
echo --- 安装后端依赖 ---
cd /d "%~dp0backend"
pip install fastapi uvicorn sse_starlette pyaudio faster-whisper edge-tts
pip install mediapipe httpx qrcode[pil] pillow
if %errorlevel% neq 0 (
    echo [^!] 后端依赖安装失败
    pause
    exit /b 1
)
echo [OK] 后端依赖安装完成

echo.
echo --- 安装前端依赖 ---
cd /d "%~dp0frontend"
npm install
if %errorlevel% neq 0 (
    echo [^!] 前端依赖安装失败
    pause
    exit /b 1
)
echo [OK] 前端依赖安装完成

echo.
echo ============================================
echo   安装完成！启动方式见 README.md
echo ============================================
pause
