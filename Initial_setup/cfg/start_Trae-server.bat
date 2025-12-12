@echo off
title Django Server Starter

:: 设置目标路径（注意手动输入正确路径）
cd /d "D:\MyTrae\servogun2"

:: 检查虚拟环境是否存在
if not exist "venv\Scripts\activate" (
    echo 虚拟环境未找到，请确保 venv 存在。
    pause
    exit /b
)

:: 激活虚拟环境
call "venv\Scripts\activate"

:: 启动服务器
python manage.py runserver 0.0.0.0:6931

:: 结束提示
echo.
echo 服务器已启动，按任意键关闭窗口...
pause >nul