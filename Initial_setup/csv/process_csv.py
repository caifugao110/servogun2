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
import sys
import time

# 启用实时打印（防止缓冲区导致看不到输出）
sys.stdout.reconfigure(line_buffering=True)

# 当前时间戳打印
def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# 常见编码列表，按优先级尝试
ENCODINGS = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin1', 'cp1252']

# 严格指定的表头顺序
STANDARD_COLUMNS = [
    "描述",
    "图号1(o)",
    "产品子分类类型",
    "行程",
    "电极臂端部",
    "加压力",
    "电极臂",
    "变压器",
    "重量",
    "变压器放置方向",
    "法兰P.C.D",
    "托架方向",
    "托架角度",
    "MOTOR厂家",
    "托架个数",
    "齿轮箱型式",
    "托架材料",
    "齿轮箱行程",
    "换枪装置",
    "喉深",
    "有无平衡",
    "喉宽",
    "水路",
    "握杆伸出长度",
    "偏心距离",
    "偏心方向",
    "偏心是否回到中心面",
    "导向方式",
    "静臂偏心",
    "静电极臂端部",
    "动臂偏心",
    "动电极臂端部",
    "支轴到驱动中心距离",
    "静电极臂前部长",
    "静电极臂前部高",
    "动电极臂前部长",
    "动电极臂前部高"
]

def read_csv_with_encoding(file_path):
    """自动尝试多种编码方式读取CSV"""
    for enc in ENCODINGS:
        try:
            with open(file_path, mode='r', newline='', encoding=enc) as f:
                reader = csv.reader(f)
                rows = list(reader)
                return rows, enc
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("无法识别文件编码，请手动检查。")

def process_header(header):
    """处理表头：修改包含特定字符串的表头"""
    processed_header = []
    for col in header:
        #处理表头：仅当列名完全等于'偏心'时改为'偏心距离'
        if col == "偏心":
            processed_header.append("偏心距离")
        # 处理包含"分类"的表头
        elif "分类" in col:
            processed_header.append("产品子分类类型")
        # 处理包含"P.C.D"的表头
        elif "P.C.D" in col:
            processed_header.append("法兰P.C.D")
        else:
            processed_header.append(col)
    return processed_header

def process_csv(file_path, file_name):
    log(f"正在处理文件：{file_name}")
    if not os.path.exists(file_path):
        log(f"❌ 文件 {file_name} 不存在，跳过处理。")
        return
    try:
        # 自动识别编码
        rows, detected_enc = read_csv_with_encoding(file_path)
        log(f"✅ 文件 {file_name} 使用编码 '{detected_enc}' 成功读取")
        if len(rows) < 2:
            log(f"⚠️ 文件 {file_name} 数据为空或格式不正确。")
            return
        
        # 处理表头
        original_header = rows[0]
        processed_header = process_header(original_header)
        
        # 创建原始列名到索引的映射
        header_index_map = {col: idx for idx, col in enumerate(original_header)}
        
        # 处理数据行
        processed_data = []
        for row in rows[1:]:  # 跳过表头
            # 创建标准结构的行数据
            standard_row = [""] * len(STANDARD_COLUMNS)
            
            # 填充已有列的数据
            for std_idx, std_col in enumerate(STANDARD_COLUMNS):
                # 查找原始列中对应的索引
                original_col_index = None
                for orig_idx, orig_col in enumerate(original_header):
                    processed_orig_col = process_header([orig_col])[0]  # 处理单个原始列名
                    if processed_orig_col == std_col:
                        original_col_index = orig_idx
                        break
                
                if original_col_index is not None and original_col_index < len(row):
                    # 处理图号1(o)列的特殊逻辑
                    if std_col == "图号1(o)":
                        value = row[original_col_index].strip()
                        # 检查是否需要删除该行（最后一个字符是"R"）
                        if value and value[-1] == 'R':
                            break  # 跳过此行
                        # 处理"(利旧)"字符串和"/"字符
                        value = value.replace("(利旧)", "").strip()
                        value = value.replace("/", "")  # 新增：删除"/"字符
                        # 只保留图号非空的行
                        if not value:
                            break
                        standard_row[std_idx] = value
                    else:
                        standard_row[std_idx] = row[original_col_index].strip()
            
            else:  # 只有当循环正常结束（没有break）时才添加此行
                processed_data.append(standard_row)

        # 添加标准表头
        final_data = [STANDARD_COLUMNS] + processed_data

        # 覆盖写回原文件（统一使用 UTF-8 编码保存）
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(final_data)
        log(f"✅ 文件 {file_name} 已成功更新，按标准表头排序并处理图号列。")
    except Exception as e:
        log(f"❌ 处理文件 {file_name} 时出错：{e}")

def main():
    current_dir = os.getcwd()
    log(f"当前工作目录：{current_dir}")
    files_to_process = [
        "X2C-C.csv",
        "X2C-V2-C.csv",
        "X2C-V3-C.csv",
        "X2C-X.CSV",
        "X2C-V2-X.CSV",
        "X2C-V3-X.CSV"
    ]
    found_any = False
    for file_name in files_to_process:
        full_path = os.path.join(current_dir, file_name)
        if os.path.exists(full_path):
            found_any = True
            process_csv(full_path, file_name)
        else:
            log(f"⚠️ 文件 {file_name} 不存在，跳过处理。")
    if not found_any:
        log("❌ 当前目录下没有找到任何需要处理的 CSV 文件。")
    else:
        log("✅ 所有存在的目标文件已处理完毕。")
    input("按回车键退出...")

if __name__ == "__main__":
    main()