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
import shutil
import csv
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ------------------ 配置：已替换为 Y: 盘映射路径 ------------------
SOURCE_DIRS = [
    r"Y:\设计一课3D资料\03-SV GUN STEP",
    r"Y:\吉利标准化\07吉利库STEP",
    r"Y:\上海3D图库拷贝文件\03-SV GUN STEP",
    r"Y:\上海3D图库拷贝文件\吉利标准化\07吉利库STEP",
    r"Y:\设计一课3D资料\01-SV GUN ASSY\13-PSA\00-STP",
    r"Y:\设计一课3D资料\01-SV GUN ASSY\16-恒大-X2CV2-TOL\STP",
    r"Y:\设计一课3D资料\01-SV GUN ASSY\17-铝焊钳\03-STP",
    r"Y:\设计一课3D资料\01-SV GUN ASSY\18-蔚来-X2CV2-TOL\STEP",
    r"Y:\设计一课3D资料\01-SV GUN ASSY\21-福建奔驰\STP",
    r"Y:\设计一课3D资料\01-SV GUN ASSY\22-印度\STP",
    r"Y:\设计一课3D资料\01-SV GUN ASSY\25-理想-X2CV2-TOL\STP",
    r"Y:\设计一课3D资料\01-SV GUN ASSY\26-海斯坦普\01-STP",
    r"Y:\设计一课3D资料\01-SV GUN ASSY\30-比亚迪\01-STP",
    r"Y:\设计一课3D资料\X2C V2标准化数据\000-STEP"
]

# 本地路径
current_dir = os.path.dirname(os.path.abspath(__file__))
target_dir = r"T:\Profile\tempstep"  # 修改目标目录
list_file = os.path.join(current_dir, "comparison_result.csv")  # 修改清单文件
log_file = os.path.join(current_dir, "Copy step list.csv")

os.makedirs(target_dir, exist_ok=True)

# ------------------ 工具函数：文件名清理 ------------------
def clean_filename(name):
    """清理文件名：去结尾L，去L(前部分，转小写"""
    if name.endswith("L"):
        name = name[:-1]
    if "L(" in name:
        parts = name.split("L(")
        name = parts[0]
    return name.lower()

# ------------------ 清理目标目录 ------------------
print("🧹 清理目标目录...")
clean_count = 0
for file in os.listdir(target_dir):
    if file.lower().endswith(".step"):
        try:
            os.remove(os.path.join(target_dir, file))
            clean_count += 1
        except Exception as e:
            print(f"⚠️ 删除旧文件失败: {file} - {e}")
print(f"✅ 已清理 {clean_count} 个旧文件")

# ------------------ 构建索引：按前4字符分组，保留优先级 ------------------
print("⏳ 正在构建全局索引...")
index = defaultdict(list)  # prefix_key -> [(clean_base, src_filename, src_dir), ...]
start_time = time.time()

for src_dir in SOURCE_DIRS:
    try:
        if not os.path.exists(src_dir):
            print(f"⚠️ 路径不存在或无权限: {src_dir}")
            continue
        with os.scandir(src_dir) as entries:
            for entry in entries:
                if entry.is_file() and entry.name.lower().endswith(".step"):
                    base_name = os.path.splitext(entry.name)[0]
                    clean_base = clean_filename(base_name)
                    prefix_key = clean_base[:4] if len(clean_base) >= 4 else clean_base
                    index[prefix_key].append((clean_base, entry.name, src_dir))
    except Exception as e:
        print(f"⚠️ 目录扫描失败: {src_dir} - {e}")

index_time = time.time() - start_time
total_indexed = sum(len(v) for v in index.values())
print(f"✅ 索引完成: {len(index)} 个前缀组, {total_indexed} 个文件, 耗时 {index_time:.2f}秒")

# ------------------ 读取待处理文件列表 ------------------
try:
    with open(list_file, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头
        all_lines = []
        for row in reader:
            if row and len(row) >= 5 and row[4] == "全部不存在":  # 只处理状态为"全部不存在"的行
                all_lines.append(row[0].strip())
    print(f"📋 从comparison_result.csv中筛选出状态为'全部不存在'的行，共 {len(all_lines)} 个文件")
except Exception as e:
    print(f"🔥 CSV读取失败: {e}")
    exit(1)

total_files = len(all_lines)
print(f"📋 待处理文件数: {total_files}")

# 预处理搜索名
search_items = [(orig, clean_filename(orig)) for orig in all_lines]

# ------------------ 并行处理函数 ------------------
def process_item(item):
    original_name, search_name = item
    dst_file = os.path.join(target_dir, f"{original_name}.STEP")
    prefix_key = search_name[:4] if len(search_name) >= 4 else search_name

    # 在对应前缀组中查找
    if prefix_key in index:
        for clean_base, src_filename, src_dir in index[prefix_key]:
            if clean_base.startswith(search_name):  # ✅ 完全保持原匹配逻辑
                for attempt in range(3):
                    try:
                        src_path = os.path.join(src_dir, src_filename)
                        shutil.copy2(src_path, dst_file)
                        return {
                            "status": "success",
                            "original": original_name,
                            "copied": src_filename,
                            "source": src_dir
                        }
                    except Exception as e:
                        if attempt < 2:
                            time.sleep(2 ** attempt)
                        else:
                            return {
                                "status": "error",
                                "original": original_name,
                                "copied": f"复制失败: {e}",
                                "source": src_dir
                            }
    return {
        "status": "not_found",
        "original": original_name,
        "copied": "未找到",
        "source": ""
    }

# ------------------ 多线程执行 ------------------
print("📦 开始并行复制...")
result_log = []
found_count = 0
not_found_count = 0
copy_errors = 0

with ThreadPoolExecutor(max_workers=12) as executor:
    futures = [executor.submit(process_item, item) for item in search_items]
    completed_count = 0
    total = len(futures)
    for future in as_completed(futures):
        result = future.result()
        result_log.append(result)
        if result["status"] == "success":
            found_count += 1
        elif result["status"] == "not_found":
            not_found_count += 1
        elif result["status"] == "error":
            copy_errors += 1
        completed_count += 1
        if completed_count % 10 == 0 or completed_count == total:
            print(f"⏳ 复制中: {completed_count}/{total} 文件")

# ------------------ 写入日志 ------------------
print("📝 写入日志...")
with open(log_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["原始文件名", "实际复制文件名", "来源路径"])
    for res in result_log:
        writer.writerow([res["original"], res["copied"], res["source"]])

# ------------------ 输出统计 ------------------
total_time = time.time() - start_time
print("\n" + "=" * 60)
print(f"✅ 操作完成! 结果已保存至: {log_file}")
print(f"📝 处理统计:")
print(f"  总文件数: {total_files}")
print(f"  ✅ 成功复制: {found_count} ({found_count/total_files:.1%})")
print(f"  ❌ 未找到: {not_found_count} ({not_found_count/total_files:.1%})")
print(f"  ⚠️ 复制错误: {copy_errors}")
print(f"⏱️ 总耗时: {total_time:.1f}秒 | 平均速度: {total_files / max(1, total_time):.1f} 文件/秒")
print("=" * 60)

if (not_found_count + copy_errors) / max(1, total_files) > 0.5:
    print("\n⚠️ 警告: 超过50%的文件处理失败！请检查 Y: 盘连接状态。")