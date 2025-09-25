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
Coze API 焊枪图号查询服务
用于通过自然语言查询焊枪图号
"""

import json
import time
import re
import requests
from django.conf import settings


def get_config():
    """获取配置信息"""
    return {
        "api_url": "https://api.coze.cn/v3/chat",
        "retrieve_url": "https://api.coze.cn/v3/chat/retrieve",
        "message_list_url": "https://api.coze.cn/v3/chat/message/list",
        "bot_id": getattr(settings, 'COZE_BOT_ID', "7551581399242522659"),
        "api_token": getattr(settings, 'COZE_API_TOKEN', "pat_d5qyMKhw2qzTEeUV2xoYbrA9GbezLlFX0tl77uNHO5HlpRD6u7qzRASGHWMnDw3A"),
        "user_id": getattr(settings, 'COZE_USER_ID', "coze_api_test_user")
    }


def get_headers(config):
    """获取请求头"""
    return {
        "Authorization": f"Bearer {config['api_token']}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def get_chat_details(config, conversation_id, chat_id):
    """获取对话详情"""
    headers = get_headers(config)
    
    params = {
        "conversation_id": conversation_id,
        "chat_id": chat_id
    }
    
    try:
        response = requests.get(
            config["retrieve_url"],
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"获取对话详情失败: {str(e)}")
        return None


def get_message_list(config, conversation_id, chat_id):
    """获取消息列表"""
    headers = get_headers(config)
    
    params = {
        "conversation_id": conversation_id,
        "chat_id": chat_id
    }
    
    try:
        response = requests.get(
            config["message_list_url"],
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"获取消息列表失败: {str(e)}")
        return None


def process_result(raw_result):
    """处理原始结果，提取图号"""
    # 先尝试提取图号，而不是先判断"未找到"
    # 查找冒号位置，提取后面的内容（包括中文冒号）
    colon_index = raw_result.find(':')
    if colon_index == -1:
        colon_index = raw_result.find('：')  # 处理中文冒号
        
    if colon_index != -1:
        content_after_colon = raw_result[colon_index+1:].strip()
    else:
        content_after_colon = raw_result.strip()
    
    # 提取所有图号（假设图号格式为字母+数字+符号组合）
    pattern = r'\b[A-Z]{2,4}-(?:[235]C|AC|C|SC|RC|EC|ZC|EX|ZX|ZC|AZ|BR)\d{1,5}[A-Z]{0,2}L?\b'
    matches = list(set(re.findall(pattern, content_after_colon)))
    
    # 如果找到匹配的图号，直接返回
    if matches:
        return ", ".join(sorted(matches)) # 排序以保持一致性
    
    # 检查是否为"未找到符合要求的焊枪"
    if "未找到符合要求的焊枪" in raw_result:
        return "未找到符合要求的焊枪"
    
    # 尝试提取逗号分隔的内容
    parts = [p.strip() for p in content_after_colon.split(',') if p.strip()]
    if parts and all(len(part) > 0 for part in parts):
        return ', '.join(parts)
    
    # 作为最后的手段，返回处理后的内容（至少让用户看到原始结果）
    return content_after_colon


def query_coze(query_text):
    """查询Coze API并返回处理后的结果"""
    config = get_config()
    headers = get_headers(config)
    
    # 发送查询消息
    payload = {
        "bot_id": config["bot_id"],
        "user_id": config["user_id"],
        "stream": False,
        "auto_save_history": True,
        "additional_messages": [
            {
                "role": "user",
                "content": query_text,
                "content_type": "text",
                "type": "question"
            }
        ]
    }
    
    try:
        response = requests.post(
            config["api_url"],
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"查询失败，状态码: {response.status_code}，响应内容: {response.text}"
            }
        
        response_data = response.json()
        
        if "data" not in response_data:
            return {
                "success": False,
                "error": "响应格式错误，缺少data字段"
            }
        
        data = response_data["data"]
        conversation_id = data.get("conversation_id")
        chat_id = data.get("id")
        
        if not conversation_id or not chat_id:
            return {
                "success": False,
                "error": "响应中缺少必要的ID信息"
            }
        
        # 等待处理完成并获取结果
        max_retries = 20
        retry_count = 0
        
        while retry_count < max_retries:
            # 获取对话详情
            details = get_chat_details(config, conversation_id, chat_id)
            
            if details and "data" in details:
                status = details["data"].get("status")
                
                if status == "completed":
                    # 对话完成，获取消息列表
                    messages = get_message_list(config, conversation_id, chat_id)
                    if messages and "data" in messages:
                        for msg in messages["data"]:
                            if msg.get("role") == "assistant":
                                raw_content = msg.get("content", "")
                                # 处理原始内容
                                processed_result = process_result(raw_content)
                                return {
                                    "success": True,
                                    "data": processed_result,
                                    "raw_content": raw_content
                                }
                elif status == "failed":
                    return {
                        "success": False,
                        "error": "对话处理失败"
                    }
            
            time.sleep(3)
            retry_count += 1
        
        return {
            "success": False,
            "error": "等待超时，未收到AI回复"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"查询过程异常: {str(e)}"
        }
