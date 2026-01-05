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

import logging
from django.http import HttpRequest

from .models import Log

logger = logging.getLogger('clamps')

def get_client_ip(request: HttpRequest) -> str:
    """获取客户端真实IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR', '')

class LoggingMiddleware:
    """日志记录中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        # 记录访问日志
        try:
            # 排除登录相关路径，提高登录性能
            if not request.path.startswith('/login'):
                user = request.user if request.user.is_authenticated else None
                ip_address = get_client_ip(request)
                
                # 只记录特定路径的访问
                if any(request.path.startswith(prefix) for prefix in ['/search', '/product', '/management']):
                    Log.objects.create(
                        user=user,
                        action_type='access',
                        details=f"访问页面: {request.path}",
                        ip_address=ip_address,
                        path=request.path,
                        method=request.method
                    )
                
                # 更新用户最后活动时间
                if request.user.is_authenticated:
                    from django.utils import timezone
                    # 使用select_related减少数据库查询
                    profile = request.user.profile
                    profile.last_activity = timezone.now()
                    profile.save(update_fields=['last_activity'])
        except Exception as e:
            logger.error(f"记录访问日志或更新最后活动时间失败: {e}")
        
        return self.get_response(request)

