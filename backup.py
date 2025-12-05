#!/usr/bin/env python
"""
备份脚本：定时备份数据库和media文件夹
- 每天10点执行备份
- 备份文件为压缩包，包含详细时间戳
- 自动清理30天前的备份文件
"""

import os
import shutil
import zipfile
import datetime
import schedule
import time
import logging
from pathlib import Path

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / 'logs' / 'backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 备份配置
BACKUP_DIR = BASE_DIR / 'backups'
MEDIA_DIR = BASE_DIR / 'media'
DB_FILE = BASE_DIR / 'db.sqlite3'
RETENTION_DAYS = 30
BACKUP_TIME = "10:00"


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


def sync_files():
    """执行文件同步"""
    try:
        # 确保Django环境已初始化
        import os
        import sys
        
        # 添加项目根目录到Python路径
        sys.path.append(str(BASE_DIR))
        
        # 设置Django环境变量
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'welding_clamp_db.settings')
        
        # 初始化Django
        import django
        django.setup()
        
        # 导入并调用文件同步核心函数
        from clamps.views import sync_files_core
        success, msg = sync_files_core()
        
        if success:
            logger.info(f"文件同步成功: {msg}")
        else:
            logger.error(f"文件同步失败: {msg}")
            
    except Exception as e:
        logger.error(f"文件同步执行失败: {str(e)}")


def daily_task():
    """每日任务：备份数据库和同步文件"""
    logger.info("开始执行每日任务")
    create_backup()
    sync_files()
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


def run_backup():
    """运行备份和文件同步，用于手动执行或系统定时任务调用"""
    logger.info("开始执行备份和文件同步任务")
    daily_task()
    logger.info("备份和文件同步任务执行完成")


def start_scheduler():
    """启动调度器"""
    # 每天10点执行备份和文件同步
    schedule.every().day.at(BACKUP_TIME).do(daily_task)
    logger.info(f"调度器已启动，每天{BACKUP_TIME}执行数据库备份和文件同步")
    
    # 立即执行一次备份和文件同步
    logger.info("立即执行一次数据库备份和文件同步")
    daily_task()
    
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
