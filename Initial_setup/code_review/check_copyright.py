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
import fnmatch

# 定义要检查的目录和文件类型
CHECK_DIRS = [
    r'd:\MyTrae\servogun2',
]

# 要排除的目录
EXCLUDE_DIRS = [
    '__pycache__',
    '.git',
    'venv',
    'node_modules',
    'migrations',  # 已处理过迁移文件
]

# 要检查的文件类型
CHECK_FILES = [
    '*.py',
    '*.bat',
]

# 版权声明标识
PYTHON_COPYRIGHT_MARKER = '# Copyright'
BAT_COPYRIGHT_MARKER = ':: Copyright'

def is_excluded(dir_path):
    """检查目录是否需要排除"""
    for exclude in EXCLUDE_DIRS:
        if exclude in dir_path.split(os.sep):
            return True
    return False

def check_file_copyright(file_path):
    """检查文件是否有版权声明"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if file_path.endswith('.py'):
            return PYTHON_COPYRIGHT_MARKER in content
        elif file_path.endswith('.bat'):
            return BAT_COPYRIGHT_MARKER in content
        else:
            return False
    except Exception as e:
        print(f'✗ Error checking {file_path}: {e}')
        return False

def main():
    """主函数"""
    print('=== Checking copyright headers in all key files ===')
    print()
    
    missing_copyright = []
    
    # 遍历所有目录
    for check_dir in CHECK_DIRS:
        for root, dirs, files in os.walk(check_dir):
            # 过滤排除的目录
            dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d))]
            
            for file in files:
                # 检查文件类型
                for pattern in CHECK_FILES:
                    if fnmatch.fnmatch(file, pattern):
                        file_path = os.path.join(root, file)
                        # 检查版权声明
                        if not check_file_copyright(file_path):
                            missing_copyright.append(file_path)
    
    if missing_copyright:
        print(f'⚠ Found {len(missing_copyright)} files missing copyright headers:')
        print()
        for file_path in missing_copyright:
            print(f'  - {file_path}')
        print()
        print('You should add copyright headers to these files.')
        
        # 生成txt文件列表
        txt_file_path = os.path.join(os.path.dirname(__file__), 'missing_copyright_files.txt')
        with open(txt_file_path, 'w', encoding='utf-8') as f:
            for file_path in missing_copyright:
                f.write(file_path + '\n')
        print(f'\n📋 Generated file list: {txt_file_path}')
    else:
        print('✓ All key files have copyright headers!')
        
        # 如果所有文件都有版权，清空或创建空的txt文件
        txt_file_path = os.path.join(os.path.dirname(__file__), 'missing_copyright_files.txt')
        with open(txt_file_path, 'w', encoding='utf-8') as f:
            f.write('')
        print(f'\n📋 Generated empty file list: {txt_file_path}')
    
    print()
    print('=== Copyright check completed ===')

if __name__ == '__main__':
    main()
