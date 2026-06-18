@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"
echo 启动前端...
npm run dev
pause
