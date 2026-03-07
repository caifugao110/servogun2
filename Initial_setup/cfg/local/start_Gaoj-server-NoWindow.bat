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

:: Create a temporary VBScript file to run the server in the background
echo Set objShell = CreateObject("WScript.Shell") > temp_run_server.vbs
echo objShell.Run "cmd /c cd /d ""D:\MyTrae\servogun2"" && python manage.py runserver 0.0.0.0:6931", 0 >> temp_run_server.vbs
echo WScript.Quit >> temp_run_server.vbs

:: Run the VBScript
cscript //nologo temp_run_server.vbs

:: Delete the temporary VBScript file
del temp_run_server.vbs

:: End message
echo Server started in background. Access at: http://localhost:6931/