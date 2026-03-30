# 前端自动重启脚本
# 使用方法: 双击运行或在 PowerShell 中运行 ./start_frontend.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  闲鱼 SaaS 前端开发服务器 (自动重启)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 进入项目目录
Set-Location D:\xianyu-saas\frontend

# 检查 node_modules 是否存在
if (!(Test-Path "node_modules")) {
    Write-Host "正在安装依赖..." -ForegroundColor Yellow
    npm install
}

Write-Host "启动开发服务器..." -ForegroundColor Green
Write-Host "文件修改后将自动重启" -ForegroundColor Yellow
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Gray
Write-Host ""

# 使用 nodemon 启动（监视配置文件变更自动重启）
npx nodemon
