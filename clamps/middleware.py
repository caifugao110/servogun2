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



from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User
from .models import Log
import logging

logger = logging.getLogger('clamps')

def get_client_ip(request):
    """获取客户端真实IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class LoggingMiddleware(MiddlewareMixin):
    """日志记录中间件"""
    
    def process_request(self, request):
        # 记录访问日志
        try:
            user = request.user if request.user.is_authenticated else None
            ip_address = get_client_ip(request)
            
            # 只记录特定路径的访问
            if request.path.startswith('/search') or request.path.startswith('/product') or request.path.startswith('/management'):
                Log.objects.create(
                    user=user,
                    action_type='access',
                    details=f"访问页面: {request.path}",
                    ip_address=ip_address,
                    path=request.path,
                    method=request.method
                )
        except Exception as e:
            logger.error(f"记录访问日志失败: {e}")
        
        return None

