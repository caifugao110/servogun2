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

setlocal enabledelayedexpansion

set "project_path=T:\Servo Gun\release"

if not exist "%project_path%" (
    exit /b 1
)

if not exist "%project_path%\manage.py" (
    exit /b 1
)

echo Set objShell = CreateObject("WScript.Shell") > temp_run_server.vbs
echo objShell.Run "cmd /c cd /d ""%project_path%"" && call venv\Scripts\activate && python manage.py runserver 0.0.0.0:6931", 0 >> temp_run_server.vbs
echo WScript.Quit >> temp_run_server.vbs

cscript //nologo temp_run_server.vbs

del temp_run_server.vbs

echo Server started in background. Access at: http://localhost:6931/
