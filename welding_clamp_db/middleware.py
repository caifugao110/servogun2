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
