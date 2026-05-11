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
腾讯元器 AI 焊枪图号查询服务
用于通过自然语言查询焊枪图号
"""

import json
import re
import hashlib
import requests
from django.conf import settings
from django.core.cache import cache


def get_config():
    """获取配置信息"""
    return {
        "api_url": "https://open.hunyuan.tencent.com/openapi/v1/agent/chat/completions",
        "assistant_id": getattr(settings, 'YUANQI_ASSISTANT_ID', ""),
        "api_key": getattr(settings, 'YUANQI_API_KEY', ""),
        "user_id": getattr(settings, 'YUANQI_USER_ID', "obara_gun_selection_user")
    }


def get_headers(config):
    """获取请求头"""
    return {
        "X-Source": "openapi",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}"
    }


def process_result(raw_result):
    """处理原始结果，提取图号"""
    colon_index = raw_result.find(':')
    if colon_index == -1:
        colon_index = raw_result.find('：')

    if colon_index != -1:
        content_after_colon = raw_result[colon_index+1:].strip()
    else:
        content_after_colon = raw_result.strip()

    pattern = r'\b[A-Z]{2,4}-(?:[235]C|AC|C|SC|RC|EC|ZC|EX|ZX|ZC|AZ|BR)\d{1,5}[A-Z]{0,2}L?\b'
    matches = list(set(re.findall(pattern, content_after_colon)))

    if matches:
        return ", ".join(sorted(matches))

    if "未找到符合要求的焊枪" in raw_result:
        return "未找到符合要求的焊枪"

    parts = [p.strip() for p in content_after_colon.split(',') if p.strip()]
    if parts and all(len(part) > 0 for part in parts):
        return ', '.join(parts)

    return content_after_colon


def query_yuanqi(query_text):
    """查询腾讯元器API并返回处理后的结果"""
    query_hash = hashlib.md5(query_text.encode('utf-8')).hexdigest()
    cache_key = f"yuanqi_query_{query_hash}"

    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    config = get_config()
    headers = get_headers(config)

    enhanced_query = f"""请严格按以下要求执行搜索：
1. 搜索条件：{query_text}
2. 请尽可能多地返回所有符合条件的焊枪图号，最多返回20个结果
3. 如果找到多个结果，请用逗号分隔列出所有图号，格式为：图号1, 图号2, 图号3...
4. 如果没有找到符合条件的结果，请回复：未找到符合要求的焊枪
5. 只返回图号列表，不需要其他解释说明"""

    payload = {
        "assistant_id": config["assistant_id"],
        "user_id": config["user_id"],
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": enhanced_query
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            config["api_url"],
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            result = {
                "success": False,
                "error": f"查询失败，状态码: {response.status_code}，响应内容: {response.text}"
            }
            return result

        response_data = response.json()

        if "choices" not in response_data or not response_data["choices"]:
            result = {
                "success": False,
                "error": "响应格式错误，缺少choices字段"
            }
            return result

        raw_content = response_data["choices"][0].get("message", {}).get("content", "")

        if not raw_content:
            result = {
                "success": False,
                "error": "未收到AI回复内容"
            }
            return result

        processed_result = process_result(raw_content)
        result = {
            "success": True,
            "data": processed_result,
            "raw_content": raw_content
        }

        cache.set(cache_key, result, timeout=1800)
        return result

    except requests.exceptions.Timeout:
        result = {
            "success": False,
            "error": "请求超时，请稍后重试"
        }
        return result
    except Exception as e:
        result = {
            "success": False,
            "error": f"查询过程异常: {str(e)}"
        }
        return result
