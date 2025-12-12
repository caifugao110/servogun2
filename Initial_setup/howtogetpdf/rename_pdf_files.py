import os

# 定义目标文件夹路径
target_folder = r"T:\Profile\temppdf"

# 检查文件夹是否存在
if not os.path.exists(target_folder):
    print(f"目标文件夹不存在: {target_folder}")
    exit(1)

# 查找所有包含逗号的文件
print(f"\n=== 查找所有包含逗号的文件 ===")
comma_files = [f for f in os.listdir(target_folder) if ',' in f]
if comma_files:
    print(f"找到 {len(comma_files)} 个包含逗号的文件:")
    for f in comma_files[:10]:  # 只显示前10个
        print(f"  - {repr(f)}")
    if len(comma_files) > 10:
        print(f"    ... 还有 {len(comma_files) - 10} 个文件")
else:
    print("未找到包含逗号的文件")

# 执行批量重命名功能
print(f"\n=== 执行批量重命名 ===")
# 获取文件夹内所有PDF文件
pdf_files = [f for f in os.listdir(target_folder) if f.lower().endswith('.pdf')]
print(f"找到 {len(pdf_files)} 个PDF文件")

# 处理文件名包含逗号的文件
renamed_count = 0
for pdf_file in pdf_files:
    # 检查文件名是否包含逗号
    if ',' in pdf_file:
        # 提取逗号之前的部分作为新文件名
        new_name = pdf_file.split(',')[0] + '.pdf'
        old_path = os.path.join(target_folder, pdf_file)
        new_path = os.path.join(target_folder, new_name)
        
        # 执行重命名
        try:
            os.rename(old_path, new_path)
            print(f"重命名成功: {pdf_file} -> {new_name}")
            renamed_count += 1
        except Exception as e:
            print(f"重命名失败 {pdf_file}: {e}")

print(f"\n处理完成，共重命名 {renamed_count} 个文件")
