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

import os
import io
import zipfile
import tempfile
import uuid
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Product, CompressionTask


def process_compression_task(task_id):
    """处理压缩任务"""
    channel_layer = get_channel_layer()
    
    # 不打印开始处理压缩任务的信息
    try:
        task = CompressionTask.objects.get(task_id=task_id)
        product_ids = [int(pid) for pid in task.product_ids.split(',') if pid.strip().isdigit()]
        file_type = task.file_type
        
        # 更新任务状态为处理中
        task.status = 'processing'
        task.progress = 10
        task.save()
        
        # 尝试发送状态更新，处理Redis连接失败情况
        try:
            # 发送状态更新
            async_to_sync(channel_layer.group_send)(
                f'compression_{task.user_id}',
                {
                    'type': 'compression_update',
                    'task_id': str(task_id),
                    'progress': 10,
                    'status': 'processing',
                    'message': '开始准备文件...'
                }
            )
        except Exception as ws_error:
            # WebSocket通知失败，继续执行压缩任务
            pass
        
        products = Product.objects.filter(id__in=product_ids)
        
        # 计算实际需要处理的文件总数
        total_files = 0
        for product in products:
            if file_type in ['pdf', 'both'] and product.pdf_file_path:
                total_files += 1
            if file_type in ['step', 'both'] and product.step_file_path:
                total_files += 1
            if file_type == 'bmp' and product.bmp_file_path:
                total_files += 1
        
        # 如果没有需要处理的文件，设置为1避免除以零
        if total_files == 0:
            total_files = 1
        
        processed_files = 0
        
        # 创建临时目录存储压缩文件
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_file_path = os.path.join(tmpdir, f'compressed_{task_id}.zip')
            
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for product in products:
                    # 根据文件类型处理
                    if file_type in ['pdf', 'both']:
                        if product.pdf_file_path:
                            # 处理PDF文件
                            pdf_path = str(product.pdf_file_path)
                            
                            # 处理不同格式的路径前缀
                            if pdf_path.startswith('media/'):
                                pdf_path = pdf_path[len('media/'):]
                            elif pdf_path.startswith('/media/'):
                                pdf_path = pdf_path[len('/media/'):]
                            elif pdf_path.startswith('\\media\\'):
                                pdf_path = pdf_path[len('\\media\\'):]
                            
                            # 构建完整路径
                            full_pdf_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
                            
                            if os.path.exists(full_pdf_path):
                                # 获取原始文件名并将后缀改为大写
                                original_filename = os.path.basename(full_pdf_path)
                                filename, ext = os.path.splitext(original_filename)
                                uppercase_filename = f"{filename}{ext.upper()}"
                                
                                try:
                                    # 为PDF文件添加水印
                                    from django.utils import timezone
                                    # 获取用户名，CompressionTask模型只有user_id字段，没有user属性
                                    try:
                                        from django.contrib.auth.models import User
                                        user = User.objects.get(id=task.user_id)
                                        username = user.username
                                    except (User.DoesNotExist, AttributeError):
                                        username = 'unknown'
                                    watermark_text = f"For Reference Only[OBARA] {username} {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')}"
                                    
                                    # 使用唯一的临时文件名，避免冲突
                                    import uuid
                                    unique_id = uuid.uuid4().hex[:8]
                                    temp_watermarked_pdf_path = os.path.join(tmpdir, f"watermarked_{unique_id}_{uppercase_filename}")
                                    
                                    from .pdf_utils import PDFProcessor
                                    
                                    # 优化：确保临时目录可写
                                    if not os.path.exists(tmpdir):
                                        os.makedirs(tmpdir, exist_ok=True)
                                    
                                    # 为大型PDF添加内存优化
                                    from PyPDF2 import PdfReader, PdfWriter
                                    
                                    # 1. 创建水印PDF（使用BytesIO避免磁盘I/O）
                                    watermark_buffer = io.BytesIO()
                                    PDFProcessor.create_watermark(watermark_text, watermark_buffer)
                                    watermark_buffer.seek(0)
                                    
                                    # 2. 读取水印页面
                                    watermark_pdf = PdfReader(watermark_buffer)
                                    watermark_page = watermark_pdf.pages[0]
                                    
                                    # 3. 处理原始PDF，逐页添加水印
                                    reader = PdfReader(full_pdf_path)
                                    writer = PdfWriter()
                                    
                                    for i in range(len(reader.pages)):
                                        page = reader.pages[i]
                                        # 优化：使用merge_transformed_page替代merge_page，提高兼容性
                                        try:
                                            # 尝试使用merge_transformed_page（PyPDF2 3.x推荐）
                                            page.merge_transformed_page(watermark_page, (1, 0, 0, 1, 0, 0))
                                        except AttributeError:
                                            # 回退到merge_page（旧版本PyPDF2）
                                            page.merge_page(watermark_page)
                                        writer.add_page(page)
                                    
                                    # 4. 写入带水印的PDF到临时文件
                                    with open(temp_watermarked_pdf_path, "wb") as output_file:
                                        writer.write(output_file)
                                    
                                    # 5. 添加带水印的PDF到压缩包
                                    zipf.write(temp_watermarked_pdf_path, uppercase_filename)
                                    processed_files += 1
                                    
                                except Exception as pdf_error:
                                    # 详细记录错误日志
                                    print(f"水印添加失败: {str(pdf_error)}，文件: {uppercase_filename}")
                                    # 水印添加失败，尝试添加原始PDF文件
                                    try:
                                        zipf.write(full_pdf_path, uppercase_filename)
                                        processed_files += 1
                                    except Exception as original_error:
                                        # 原始文件也无法添加，只增加计数器
                                        processed_files += 1
                                finally:
                                    # 清理临时文件，添加异常处理
                                    try:
                                        if 'temp_watermarked_pdf_path' in locals() and os.path.exists(temp_watermarked_pdf_path):
                                            os.remove(temp_watermarked_pdf_path)
                                    except Exception as cleanup_error:
                                        print(f"清理临时文件失败: {str(cleanup_error)}")
                            
                    if file_type in ['step', 'both']:
                        if product.step_file_path:
                            # 处理STEP文件
                            step_path = product.step_file_path
                            if str(step_path).startswith('media/'):
                                step_path = str(step_path)[len('media/'):]
                            full_step_path = os.path.join(settings.MEDIA_ROOT, step_path)
                            
                            if os.path.exists(full_step_path):
                                # 获取原始文件名并将后缀改为大写
                                original_filename = os.path.basename(full_step_path)
                                filename, ext = os.path.splitext(original_filename)
                                uppercase_filename = f"{filename}{ext.upper()}"
                                # 添加到压缩包
                                zipf.write(full_step_path, uppercase_filename)
                                processed_files += 1
                    
                    if file_type == 'bmp':
                        if product.bmp_file_path:
                            # 处理BMP文件
                            bmp_path = product.bmp_file_path
                            if str(bmp_path).startswith('media/'):
                                bmp_path = str(bmp_path)[len('media/'):]
                            full_bmp_path = os.path.join(settings.MEDIA_ROOT, bmp_path)
                            
                            if os.path.exists(full_bmp_path):
                                # 获取原始文件名并将后缀改为大写
                                original_filename = os.path.basename(full_bmp_path)
                                filename, ext = os.path.splitext(original_filename)
                                uppercase_filename = f"{filename}{ext.upper()}"
                                # 添加到压缩包
                                zipf.write(full_bmp_path, uppercase_filename)
                                processed_files += 1
                    
                    # 更新进度
                    progress = 10 + int((processed_files / total_files) * 80)
                    task.progress = min(progress, 90)  # 保留10%用于后续处理
                    task.save()
                    
                    # 尝试发送进度更新，处理Redis连接失败情况
                    try:
                        # 发送进度更新
                        async_to_sync(channel_layer.group_send)(
                            f'compression_{task.user_id}',
                            {
                                'type': 'compression_update',
                                'task_id': str(task_id),
                                'progress': task.progress,
                                'status': 'processing',
                                'message': f'已处理 {processed_files}/{total_files} 个文件'
                            }
                        )
                    except Exception as ws_error:
                        # WebSocket通知失败，继续执行压缩任务
                        pass
            
            # 保存压缩文件到指定位置
            from pathlib import Path
            BASE_DIR = Path(__file__).resolve().parent.parent
            temp_dir = os.path.join(BASE_DIR, 'temp')
            compressed_files_dir = os.path.join(temp_dir, 'compressed_files')
            os.makedirs(compressed_files_dir, exist_ok=True)
            
            # 生成唯一的压缩文件名
            unique_filename = f'{task_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.zip'
            dest_path = os.path.join(compressed_files_dir, unique_filename)
            
            # 将临时文件复制到目标位置
            import shutil
            shutil.copy2(zip_file_path, dest_path)
            
            # 更新任务状态
            task.status = 'completed'
            task.progress = 100
            task.compressed_file_path = f'temp/compressed_files/{unique_filename}'
            task.save()
            
            # 尝试发送完成通知，处理Redis连接失败情况
            try:
                # 发送完成通知
                async_to_sync(channel_layer.group_send)(
                    f'compression_{task.user_id}',
                    {
                        'type': 'compression_update',
                        'task_id': str(task_id),
                        'progress': 100,
                        'status': 'completed',
                        'message': '压缩完成，准备下载...'
                    }
                )
            except Exception as ws_error:
                # WebSocket通知失败，继续执行
                pass
    
    except Exception as e:
        print(f"压缩任务{task_id}处理失败: {e}")
        # 更新任务状态为失败
        try:
            task = CompressionTask.objects.get(task_id=task_id)
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
            
            # 尝试发送错误通知，处理Redis连接失败情况
            try:
                # 发送错误通知
                async_to_sync(channel_layer.group_send)(
                    f'compression_{task.user_id}',
                    {
                        'type': 'compression_update',
                        'task_id': str(task_id),
                        'progress': 0,
                        'status': 'failed',
                        'message': f'压缩失败: {str(e)}'
                    }
                )
            except Exception as ws_error:
                # WebSocket通知失败，记录错误
                pass
        except Exception as update_error:
            print(f"更新任务状态失败: {update_error}")
