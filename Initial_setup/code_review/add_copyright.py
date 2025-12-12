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

# 定义版权声明内容
PYTHON_COPYRIGHT = '''# Copyright [2025] [OBARA (Nanjing) Electromechanical Co., Ltd]
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
'''

BAT_COPYRIGHT = ''':: Copyright [2025] [OBARA (Nanjing) Electromechanical Co., Ltd]
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
'''

# 从txt文件读取要处理的文件列表
def get_files_to_process():
    """从missing_copyright_files.txt获取要处理的文件列表"""
    txt_file_path = os.path.join(os.path.dirname(__file__), 'missing_copyright_files.txt')
    if not os.path.exists(txt_file_path):
        print(f'⚠ File not found: {txt_file_path}')
        print('Please run check_copyright.py first to generate the file list.')
        return []
    
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        files = [line.strip() for line in f if line.strip()]
    
    return files

def add_copyright_to_python_file(file_path):
    """给Python文件添加版权声明"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有版权声明
        if not content.startswith('# Copyright'):
            # 直接在开头添加版权声明
            new_content = PYTHON_COPYRIGHT + content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'✓ Added copyright to {file_path}')
        else:
            print(f'✓ Already has copyright: {file_path}')
    except Exception as e:
        print(f'✗ Error processing {file_path}: {e}')

def add_copyright_to_bat_file(file_path):
    """给批处理文件添加版权声明"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有版权声明
        if not content.startswith(':: Copyright'):
            # 检查是否有@echo off
            if content.startswith('@echo off'):
                # 保留@echo off，在其后添加版权声明
                lines = content.split('\n')
                new_content = lines[0] + '\n' + BAT_COPYRIGHT + '\n'.join(lines[1:])
            else:
                # 直接在开头添加版权声明
                new_content = BAT_COPYRIGHT + content
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'✓ Added copyright to {file_path}')
        else:
            print(f'✓ Already has copyright: {file_path}')
    except Exception as e:
        print(f'✗ Error processing {file_path}: {e}')

def main():
    """主函数"""
    print('=== Adding copyright headers to files ===')
    print()
    
    # 获取要处理的文件列表
    files_to_process = get_files_to_process()
    
    if not files_to_process:
        print('✓ No files to process.')
        print()
        print('=== All files processed ===')
        return
    
    print(f'📋 Found {len(files_to_process)} files to process:')
    print()
    
    for file_path in files_to_process:
        if file_path.endswith('.py'):
            add_copyright_to_python_file(file_path)
        elif file_path.endswith('.bat'):
            add_copyright_to_bat_file(file_path)
        else:
            print(f'✗ Unsupported file type: {file_path}')
    
    print()
    print('=== All files processed ===')

if __name__ == '__main__':
    main()
