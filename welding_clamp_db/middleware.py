from django.utils.deprecation import MiddlewareMixin

class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # 添加内容安全策略（CSP）
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';"
        
        # 添加严格传输安全（HSTS）
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # 添加Referrer策略
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # 添加X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # 添加X-XSS-Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # 添加X-Frame-Options
        response['X-Frame-Options'] = 'DENY'
        
        return response
