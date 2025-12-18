#!/usr/bin/env python
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

"""
备份脚本：定时备份数据库文件db.sqlite3
- 每天10点执行备份
- 备份文件为压缩包，包含详细时间戳
- 自动清理30天前的备份文件
"""

import os
import zipfile
import datetime
import schedule
import time
import logging
from pathlib import Path

# 获取项目根目录（因为文件在clamps目录下，所以需要上一级）
BASE_DIR = Path(__file__).resolve().parent.parent

# 导入Django相关模块（延迟导入，避免在模块加载时触发setup）
import django
from django.conf import settings
from django.utils import timezone
from clamps.models import CompressionTask

# 只在非Django启动环境下执行setup
def initialize_django():
    if not django.conf.settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'welding_clamp_db.settings')
        django.setup()

# 获取项目根目录（因为文件在clamps目录下，所以需要上一级）
BASE_DIR = Path(__file__).resolve().parent.parent

# 配置日志，只输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 备份配置
BACKUP_DIR = BASE_DIR / 'backups'
DB_FILE = BASE_DIR / 'db.sqlite3'
RETENTION_DAYS = 30
BACKUP_TIME = "00:01"

# 临时文件配置
TEMP_DIR = BASE_DIR / 'temp'
COMPRESSED_FILES_DIR = TEMP_DIR / 'compressed_files'
COMPRESSED_RETENTION_DAYS = 7


def create_backup():
    """创建备份"""
    try:
        # 确保备份目录存在
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.zip"
        backup_path = BACKUP_DIR / backup_filename
        
        # 创建压缩包
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 备份数据库文件
            zipf.write(DB_FILE, arcname=DB_FILE.name)
            logger.info(f"已备份数据库文件: {DB_FILE.name}")
        
        logger.info(f"备份完成: {backup_filename}")
        
        # 清理旧备份
        cleanup_old_backups()
        
    except Exception as e:
        logger.error(f"备份失败: {str(e)}")


def daily_task():
    """每日任务：备份数据库和清理临时文件"""
    logger.info("开始执行每日任务")
    create_backup()
    cleanup_compressed_files()
    logger.info("每日任务执行完成")


def cleanup_old_backups():
    """清理30天前的备份文件"""
    try:
        current_time = datetime.datetime.now()
        cutoff_time = current_time - datetime.timedelta(days=RETENTION_DAYS)
        
        # 遍历备份目录
        for file in os.listdir(BACKUP_DIR):
            file_path = BACKUP_DIR / file
            if file_path.is_file() and file.startswith("backup_") and file.endswith(".zip"):
                # 获取文件修改时间
                file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # 如果文件超过30天，删除
                if file_mtime < cutoff_time:
                    os.remove(file_path)
                    logger.info(f"已清理旧备份: {file}")
    
    except Exception as e:
        logger.error(f"清理旧备份失败: {str(e)}")


def cleanup_compressed_files():
    """直接清空压缩文件目录"""
    try:
        logger.info("开始清空压缩文件目录")
        
        # 确保temp目录存在
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # 确保compressed_files目录存在
        os.makedirs(COMPRESSED_FILES_DIR, exist_ok=True)
        
        file_count = 0
        total_size = 0
        
        # 直接清空compressed_files目录
        for file in os.listdir(COMPRESSED_FILES_DIR):
            file_path = COMPRESSED_FILES_DIR / file
            if file_path.is_file():
                file_size = os.path.getsize(file_path)
                file_count += 1
                total_size += file_size
                
                try:
                    os.remove(file_path)
                    logger.info(f"已删除压缩文件: {file_path} ({file_size / 1024 / 1024:.2f} MB)")
                except Exception as e:
                    logger.error(f"删除压缩文件失败: {file_path} - {str(e)}")
        
        # 删除所有压缩任务记录
        task_count = CompressionTask.objects.count()
        if task_count > 0:
            CompressionTask.objects.all().delete()
            logger.info(f"已删除所有{task_count}个压缩任务记录")
        
        logger.info(f"压缩文件目录清空完成: 删除了{file_count}个文件，总大小{total_size / 1024 / 1024:.2f}MB")
        
    except Exception as e:
        logger.error(f"清空压缩文件目录失败: {str(e)}")


def run_backup():
    """运行备份，用于手动执行或系统定时任务调用"""
    logger.info("开始执行数据库备份任务")
    create_backup()
    logger.info("数据库备份任务执行完成")


def start_scheduler():
    """启动调度器"""
    # 每天10点执行数据库备份
    schedule.every().day.at(BACKUP_TIME).do(daily_task)
    logger.info(f"调度器已启动，每天{BACKUP_TIME}执行数据库备份")
    
    # 循环执行调度任务
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    # 检查命令行参数
    import sys
    # 初始化Django环境（仅当脚本直接运行时）
    initialize_django()
    if len(sys.argv) > 1 and sys.argv[1] == "--scheduler":
        # 启动调度器
        start_scheduler()
    else:
        # 直接执行备份
        run_backup()
