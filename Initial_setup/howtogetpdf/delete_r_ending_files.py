#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 配置日志，只输出到控制台，不生成日志文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def delete_r_ending_files(media_dir: str):
    """
    删除media目录及其子目录中所有以R结尾的文件
    
    Args:
        media_dir: media目录的路径
    """
    if not os.path.exists(media_dir):
        logger.error(f"Media directory {media_dir} does not exist.")
        return 0
    
    logger.info(f"Starting to delete files ending with 'R' in {media_dir}")
    
    # 收集所有需要删除的文件路径
    files_to_delete = []
    
    # 使用os.scandir递归遍历所有文件，提高性能
    def scan_directory(directory):
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        # 递归处理子目录
                        scan_directory(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        filename = entry.name
                        # 检查文件名（不包括扩展名）是否以R结尾
                        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
                        if name_without_ext.lower().endswith('r'):
                            files_to_delete.append(entry.path)
        except PermissionError as e:
            logger.error(f"Permission denied when accessing {directory}: {e}")
        except Exception as e:
            logger.error(f"Error scanning {directory}: {e}")
    
    # 开始扫描，收集需要删除的文件
    scan_directory(media_dir)
    
    logger.info(f"Found {len(files_to_delete)} files to delete.")
    
    total_deleted = 0
    error_count = 0
    # 添加锁来保护共享资源
    lock = Lock()
    
    # 定义文件删除函数
    def delete_file(file_path):
        nonlocal total_deleted, error_count
        try:
            os.remove(file_path)
            with lock:
                total_deleted += 1
            return True, file_path, None
        except Exception as e:
            with lock:
                error_count += 1
            return False, file_path, e
    
    # 使用线程池并行删除文件
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
        # 提交所有删除任务
        future_to_file = {executor.submit(delete_file, file_path): file_path for file_path in files_to_delete}
        
        # 处理完成的任务
        for future in as_completed(future_to_file):
            success, file_path, error = future.result()
            if success:
                logger.info(f"Deleted file: {file_path}")
            else:
                logger.error(f"Failed to delete {file_path}: {error}")
    
    logger.info(f"Deletion completed. Total files deleted: {total_deleted}, Errors: {error_count}")
    return total_deleted


if __name__ == "__main__":
    # 媒体目录路径（使用相对路径）
    MEDIA_DIR = r"../../media"
    
    # 执行删除操作
    delete_r_ending_files(MEDIA_DIR)
    
    # 等待用户输入，防止控制台窗口自动关闭
    input("\nPress any key to exit...")