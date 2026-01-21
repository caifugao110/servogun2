:: Copyright [2025] [OBARA (Nanjing) Electromechanical Co., Ltd]
::
:: Licensed under the Apache License, Version 2.0 (the "License");
:: you may not use this file except in compliance with the License.
:: You may obtain a copy of the License at
::
::     http://www.apache.org/licenses/LICENSE-2.0
::
:: Unless required by applicable law or agreed to in writing, software
:: distributed under the License is distributed on an "AS IS" BASIS,
:: WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
:: See the License for the specific language governing permissions and
:: limitations under the License.

@echo off
title Django Production Server Starter

:: 自动检测IP地址并设置目标路径
@echo off
setlocal enabledelayedexpansion

:: 定义需要使用T盘路径的IP列表
set "DEBUG_DISABLE_IPS=192.168.160.21 192.168.160.25 192.168.160.61 192.168.160.62 192.168.160.63 192.168.160.67"

:: 获取本机IP地址
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /i "IPv4 Address"') do (
    for /f "tokens=1" %%j in ("%%i") do (
        set "LOCAL_IP=%%j"
        goto :IP_FOUND
    )
)
:IP_FOUND

:: 检查IP是否在特定列表中
set "TARGET_PATH=D:\MyTrae\servogun2"
for %%i in (%DEBUG_DISABLE_IPS%) do (
    if "!LOCAL_IP!"=="%%i" (
        set "TARGET_PATH=T:\Servo Gun\release"
        goto :PATH_SET
    )
)
:PATH_SET

:: 设置目标路径
cd /d "!TARGET_PATH!"

:: 检查虚拟环境是否存在
if not exist "venv\Scripts\activate" (
    echo 虚拟环境未找到，请确保 venv 存在。
    pause
    exit /b
)

:: 激活虚拟环境
call "venv\Scripts\activate"

:: 安装依赖
pip install -r requirements.txt

:: 收集静态文件
python manage.py collectstatic --noinput

:: 启动WSGI服务器
echo 正在启动生产服务器...
python initial_setup\deployment_scripts\start_wsgi.py

:: 结束提示
echo.
echo 服务器已停止，按任意键关闭窗口...
pause >nul
