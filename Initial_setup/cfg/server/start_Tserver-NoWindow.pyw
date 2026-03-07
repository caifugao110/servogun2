#!/usr/bin/env python3
# Copyright [2025] [OBARA (Nanjing) Electromechanical Co., Ltd]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess
import sys

# Set the working directory
working_dir = r"T:\Servo Gun\release"

# Create a temporary VBS script in the same directory as this script
temp_vbs = os.path.join(os.path.dirname(__file__), "temp_run_server.vbs")

# Write the VBS script content with absolute paths
activate_script = os.path.join(working_dir, "venv", "Scripts", "activate.bat")
python_exe = os.path.join(working_dir, "venv", "Scripts", "python.exe")
manage_py = os.path.join(working_dir, "manage.py")

vbs_content = f'''
Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /c cd /d \"{working_dir}\" && \"{activate_script}\" && \"{python_exe}\" \"{manage_py}\" runserver 0.0.0.0:6931", 0
WScript.Quit
'''

with open(temp_vbs, 'w', encoding='utf-8') as f:
    f.write(vbs_content)

# Run the VBS script which will start the server hidden
# Use Popen to allow the script to run in the background
subprocess.Popen(["cscript", "//nologo", temp_vbs], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)

# Give the VBS script time to start the server
import time
time.sleep(2)

# Delete the temporary VBS script
try:
    os.remove(temp_vbs)
except:
    pass

# Exit immediately without showing any output
sys.exit(0)
