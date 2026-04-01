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

from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# 解决Windows控制台编码问题
if sys.platform == 'win32':
    import io
    # 设置标准输出为UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 确保日志目录存在
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# 加载环境变量
load_dotenv(BASE_DIR / '.env')

# 安全设置
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-here-change-in-production')

# DEBUG模式：从环境变量读取，默认为False（生产环境安全优先）
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

# 从环境变量获取ALLOWED_HOSTS
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# 从环境变量获取CSRF_TRUSTED_ORIGINS
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'https://gun.obara.com.cn').split(',')

# HTTPS安全配置
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() in ('true', '1', 'yes')
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True').lower() in ('true', '1', 'yes')

# 应用配置
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'clamps',
    'channels',
]

# 中间件配置
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'clamps.middleware.RateLimitMiddleware',
    'clamps.middleware.LoggingMiddleware',
]

# URL配置
ROOT_URLCONF = 'welding_clamp_db.urls'

# 模板配置
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.media',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'welding_clamp_db.wsgi.application'
# ASGI配置
ASGI_APPLICATION = 'welding_clamp_db.asgi.application'

# Channels配置
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
        'OPTIONS': {
            'charset': os.getenv('DB_CHARSET', 'utf8mb4'),
        } if os.getenv('DB_ENGINE') in ['django.db.backends.mysql', 'django.db.backends.mysql'] else {},
    }
}

# 密码验证
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 国际化配置
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# 静态文件配置
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 默认主键类型
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 登录配置
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/search/'
LOGOUT_REDIRECT_URL = '/'

# 会话配置
SESSION_COOKIE_AGE = 3600 * 24 * 7  # 7天
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
# 会话Cookie安全设置
SESSION_COOKIE_SECURE = True  # 确保Cookie只通过HTTPS传输
SESSION_COOKIE_HTTPONLY = True  # 防止JavaScript访问Cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # 防止CSRF攻击

# 请求体大小限制
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Rate Limiting配置
MIDDLEWARE += ['django.middleware.gzip.GZipMiddleware']

# 全局速率限制设置
RATE_LIMIT = {
    'default': {
        'requests': 60,  # 每分钟最多60次请求
        'window': 60,    # 时间窗口（秒）
    },
    'search': {
        'requests': 10,  # 每分钟最多10次搜索
        'window': 60,    # 时间窗口（秒）
    }
}

# 缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# 安全响应头配置
SECURE_BROWSER_XSS_FILTER = True  # 启用XSS保护
SECURE_CONTENT_TYPE_NOSNIFF = True  # 防止MIME类型嗅探
X_FRAME_OPTIONS = 'DENY'  # 防止点击劫持

# 安全中间件配置
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # 支持代理服务器的HTTPS

# 安全响应头中间件
MIDDLEWARE += ['welding_clamp_db.middleware.SecurityHeadersMiddleware']

# 搜索频率限制
SEARCH_RATE_LIMIT = {
    'requests': 10,  # 每分钟最多10次搜索
    'window': 60,    # 时间窗口（秒）
}

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s',
        },
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{server_time}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'json_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.json.log',
            'formatter': 'json',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
    },
    'root': {
        'handlers': ['file', 'json_file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'json_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file', 'json_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'clamps': {
            'handlers': ['console', 'file', 'json_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Coze AI 配置
COZE_BOT_ID = os.getenv('COZE_BOT_ID', '')
COZE_API_TOKEN = os.getenv('COZE_API_TOKEN', '')
COZE_USER_ID = os.getenv('COZE_USER_ID', '')



