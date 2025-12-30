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



from django.apps import AppConfig
import threading
import os

class ClampsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clamps'

    def ready(self):
        # 导入信号处理模块
        from . import signals
        
        # 获取DEBUG设置
        from django.conf import settings
        
        # RUN_MAIN is None in the initial process, 'true' in the reload process
        run_main = os.environ.get('RUN_MAIN')
        
        # 只在初始进程中打印DEBUG模式（避免重复）
        if run_main is None:
            print(f"DEBUG模式: {settings.DEBUG}")
        
        # 只在主进程（reload进程）中启动调度器
        if run_main == 'true':
            # 导入备份模块并启动调度器
            import threading
            from .backup import start_scheduler
            scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
            scheduler_thread.start()
