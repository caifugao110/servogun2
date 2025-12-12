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
from pathlib import Path

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
    media_path = Path(media_dir)
    if not media_path.exists():
        logger.error(f"Media directory {media_dir} does not exist.")
        return
    
    logger.info(f"Starting to delete files ending with 'R' in {media_dir}")
    
    total_deleted = 0
    # 递归遍历所有文件
    for file_path in media_path.rglob('*'):
        if file_path.is_file():
            filename = file_path.name
            # 检查文件名（不包括扩展名）是否以R结尾
            name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            if name_without_ext.lower().endswith('r'):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted file: {file_path}")
                    total_deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
    
    logger.info(f"Deletion completed. Total files deleted: {total_deleted}")
    return total_deleted


if __name__ == "__main__":
    # 媒体目录路径
    MEDIA_DIR = r"d:\MyTrae\servogun2\media"
    
    # 执行删除操作
    delete_r_ending_files(MEDIA_DIR)