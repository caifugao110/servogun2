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
WSGI服务器启动脚本，使用Waitress作为WSGI服务器
适用于生产环境部署
"""

import os
import sys
import logging
from pathlib import Path
from waitress import serve

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 将项目根目录添加到Python路径中，确保能找到所有模块
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
    logging.info(f"Added project root to sys.path: {BASE_DIR}")

# 设置Django环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'welding_clamp_db.settings')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / 'logs' / 'wsgi_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """启动WSGI服务器"""
    try:
        # 导入Django应用
        from django.core.wsgi import get_wsgi_application
        application = get_wsgi_application()
        
        logger.info("WSGI应用初始化成功")
        logger.info("正在启动Waitress服务器...")
        
        # 启动Waitress服务器
        # 绑定到所有网络接口的6931端口
        serve(
            application,
            host='0.0.0.0',
            port=6931,
            threads=4,  # 根据服务器性能调整线程数
            connection_limit=1000,  # 连接限制
            cleanup_interval=30,  # 清理间隔
            channel_timeout=120,  # 通道超时
        )
        
    except Exception as e:
        logger.error(f"启动WSGI服务器失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
