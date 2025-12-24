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

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('clamps.urls')),
]

from django.views.static import serve

# 自定义静态文件服务视图，添加缓存头
def cached_static_serve(request, path, document_root=None):
    response = serve(request, path, document_root=document_root)
    # 设置缓存时间为一个星期
    response['Cache-Control'] = 'max-age=604800, public'
    return response

# 开发环境提供静态文件服务
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', cached_static_serve, {'document_root': settings.STATIC_ROOT}),
    ]



