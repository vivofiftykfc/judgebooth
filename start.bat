@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
echo 启动后端...
echo.
echo 按任意键启动（请先确保已设好环境变量）
echo   LLM_API_KEY / IMG_GEN_API_KEY / KMP_DUPLICATE_LIB_OK
pause >nul
uvicorn main:app --host 0.0.0.0 --port 8000
pause
