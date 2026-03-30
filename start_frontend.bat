@echo off
chcp 65001 >nul
title 闲鱼SaaS前端开发服务器
cd /d D:\xianyu-saas\frontend
echo ========================================
echo   闲鱼 SaaS 前端开发服务器 (自动重启)
echo ========================================
echo.
echo 正在启动...
npx nodemon
pause
