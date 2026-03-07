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
working_dir = "D:\MyTrae\servogun2"

# Command to run the server
cmd = [sys.executable, "manage.py", "runserver", "0.0.0.0:6931"]

# Run the server in the background
# For Windows, use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS
if os.name == 'nt':
    # For Windows, use CREATE_NO_WINDOW to completely hide the window
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    subprocess.Popen(cmd, cwd=working_dir, creationflags=creationflags, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
else:
    # For non-Windows systems, use nohup
    subprocess.Popen(["nohup"] + cmd, cwd=working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Exit immediately without showing any output
sys.exit(0)
