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