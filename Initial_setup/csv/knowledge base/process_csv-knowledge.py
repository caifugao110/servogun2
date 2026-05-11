import os
import csv

csv_files = [
    'X2C-C.csv',
    'X2C-V2-C.csv',
    'X2C-V2-X.csv',
    'X2C-V3-C.csv',
    'X2C-V3-X.csv',
    'X2C-X.csv'
]

input_dir = r'd:\MyTrae\servogun2\initial_setup\csv'
output_dir = r'd:\MyTrae\servogun2\initial_setup\csv\knowledge base'

for filename in csv_files:
    input_path = os.path.join(input_dir, filename)
    if not os.path.exists(input_path):
        print(f"文件不存在: {input_path}")
        continue
    
    base_name = os.path.splitext(filename)[0]
    output_filename = f"{base_name}-knowledge.csv"
    output_path = os.path.join(output_dir, output_filename)
    
    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        headers = next(reader)
        new_headers = []
        for header in headers:
            if header == '描述':
                new_headers.append('客户')
            elif header == '图号1(o)':
                new_headers.append('图号')
            else:
                new_headers.append(header)
        writer.writerow(new_headers)
        
        for row in reader:
            writer.writerow(row)
    
    print(f"处理完成: {filename} -> {output_filename}")

print("所有文件处理完成！")
