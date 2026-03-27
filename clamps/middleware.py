from django.utils.deprecation import MiddlewareMixin
import time
import hashlib
from django.conf import settings
from django.http import HttpResponse

class RateLimitMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        self.requests = {}
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def process_request(self, request):
        # 获取客户端IP
        client_ip = self.get_client_ip(request)
        # 生成请求标识
        request_key = f"{client_ip}:{request.path}"
        
        # 获取当前时间
        current_time = time.time()
        
        # 清理过期的请求记录
        self.requests = {k: v for k, v in self.requests.items() if current_time - v[0] < 60}
        
        # 检查速率限制
        rate_limit_config = settings.RATE_LIMIT.get('default', {'requests': 60, 'window': 60})
        
        # 如果是搜索请求，使用搜索特定的速率限制
        if 'search' in request.path:
            rate_limit_config = settings.RATE_LIMIT.get('search', rate_limit_config)
        
        # 检查请求次数
        if request_key in self.requests:
            timestamp, count = self.requests[request_key]
            if current_time - timestamp < rate_limit_config['window']:
                if count >= rate_limit_config['requests']:
                    return HttpResponse('Rate limit exceeded', status=429)
                self.requests[request_key] = (timestamp, count + 1)
            else:
                self.requests[request_key] = (current_time, 1)
        else:
            self.requests[request_key] = (current_time, 1)
        
        return None

class LoggingMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
    
    def process_request(self, request):
        # 记录请求开始时间
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        # 计算请求处理时间
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            # 可以在这里添加日志记录
        return response
