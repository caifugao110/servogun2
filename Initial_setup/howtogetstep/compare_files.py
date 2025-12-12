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
import csv
from pathlib import Path

def main():
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent
    
    # 定义路径
    csv_dir = Path(r'd:\MyTrae\servogun2\initial_setup\csv')
    media_dir = Path(r'd:\MyTrae\servogun2\media')
    output_file = current_dir / 'comparison_result.csv'
    
    # 获取所有 CSV 文件
    csv_files = list(csv_dir.glob('*.csv'))
    print(f"找到 {len(csv_files)} 个 CSV 文件")
    
    # 读取所有 CSV 文件的"图号1(o)"列
    part_numbers = set()
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # 检查列名
                if '图号1(o)' in reader.fieldnames:
                    for row in reader:
                        part_number = row['图号1(o)']
                        if part_number:
                            part_numbers.add(part_number.strip())
                else:
                    print(f"文件 {csv_file.name} 中没有'图号1(o)'列")
        except Exception as e:
            print(f"读取文件 {csv_file.name} 出错: {e}")
    
    print(f"从 CSV 文件中提取到 {len(part_numbers)} 个唯一图号")
    
    # 清理空字符串
    part_numbers = {pn.strip() for pn in part_numbers if pn.strip()}
    print(f"清理后得到 {len(part_numbers)} 个有效图号")
    
    # 获取 media 文件夹中的所有文件名，并按前缀分组
    media_files = {}
    for file_path in media_dir.glob('*.*'):
        prefix = file_path.stem
        ext = file_path.suffix.lower()
        if prefix not in media_files:
            media_files[prefix] = set()
        media_files[prefix].add(ext)
    
    print(f"在 media 文件夹中找到 {len(media_files)} 个文件前缀")
    
    # 定义需要检查的文件格式
    formats = ['.bmp', '.pdf', '.step']
    
    # 对比并生成结果
    results = []
    for part_number in sorted(part_numbers):
        # 检查每种格式是否存在
        format_status = {}
        for fmt in formats:
            format_status[fmt] = fmt in media_files.get(part_number, set())
        
        # 计算状态
        has_all = all(format_status.values())
        has_none = not any(format_status.values())
        
        # 构建结果行
        result = {
            '图号1(o)': part_number,
            '.bmp': '存在' if format_status['.bmp'] else '不存在',
            '.pdf': '存在' if format_status['.pdf'] else '不存在',
            '.step': '存在' if format_status['.step'] else '不存在',
            '状态': '全部存在' if has_all else '全部不存在' if has_none else '部分存在'
        }
        results.append(result)
    
    # 将结果保存为 CSV 文件
    fieldnames = ['图号1(o)', '.bmp', '.pdf', '.step', '状态']
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # 统计结果
    total = len(results)
    all_exist = sum(1 for r in results if r['状态'] == '全部存在')
    none_exist = sum(1 for r in results if r['状态'] == '全部不存在')
    some_exist = sum(1 for r in results if r['状态'] == '部分存在')
    
    print(f"比较完成，结果已保存到 {output_file}")
    print(f"总共有 {total} 个图号进行了比较")
    print(f"全部存在: {all_exist}")
    print(f"全部不存在: {none_exist}")
    print(f"部分存在: {some_exist}")

if __name__ == "__main__":
    main()