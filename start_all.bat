@echo off
chcp 65001 >nul
title 闲鱼SaaS 前后端启动器
cd /d D:\xianyu-saas

echo ========================================
echo   闲鱼 SaaS 前后端启动器
echo ========================================
echo.

:: 启动后端
echo [1/2] 启动后端 API (端口 8000)...
start "后端API" cmd /k "cd /d D:\xianyu-saas\backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000"

:: 等待后端启动
echo 等待后端启动...
timeout /t 3 /nobreak >nul

:: 启动前端
echo [2/2] 启动前端开发服务器 (端口 5173)...
start "前端Dev" cmd /k "cd /d D:\xianyu-saas\frontend && npm run dev"

echo.
echo ========================================
echo  启动完成！
echo  前端: http://localhost:5173
echo  后端: http://localhost:8000
echo ========================================
echo.
echo 按任意键关闭所有服务...
pause >nul

:: 关闭进程
taskkill /FI "WINDOWTITLE eq 后端API*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq 前端Dev*" /F >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
echo 服务已关闭
