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

import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync


class CompressionConsumer(WebsocketConsumer):
    """压缩任务WebSocket消费者"""
    
    def connect(self):
        # 获取用户ID
        user = self.scope['user']
        if not user.is_authenticated:
            self.close()
            return
        
        self.user_id = user.id
        # 创建组名，用于向特定用户发送压缩状态更新
        self.group_name = f'compression_{self.user_id}'
        
        # 加入组
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        
        self.accept()
    
    def disconnect(self, close_code):
        # 离开组
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )
    
    def receive(self, text_data):
        # 处理来自客户端的消息（如果需要）
        pass
    
    def compression_update(self, event):
        # 发送压缩状态更新给客户端
        self.send(text_data=json.dumps({
            'task_id': event['task_id'],
            'progress': event['progress'],
            'status': event['status'],
            'message': event['message']
        }))
