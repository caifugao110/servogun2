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
    """每日任务：备份数据库"""
    logger.info("开始执行每日备份任务")
    create_backup()
    logger.info("每日备份任务执行完成")


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
    if len(sys.argv) > 1 and sys.argv[1] == "--scheduler":
        # 启动调度器
        start_scheduler()
    else:
        # 直接执行备份
        run_backup()
