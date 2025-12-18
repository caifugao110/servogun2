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
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Product, CompressionTask, UserProfile
from .pdf_utils import PDFProcessor


@login_required
def start_compression(request):
    """开始压缩任务"""
    if request.method == 'POST':
        # Handle both form data and JSON requests
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            product_ids_str = data.get('product_ids', '')
            file_type = data.get('file_type', '')
        else:
            product_ids_str = request.POST.get('product_ids', '')
            file_type = request.POST.get('file_type', '')
        
        product_ids = [int(pid) for pid in product_ids_str.split(',') if pid.strip().isdigit()]
        
        if not product_ids or not file_type:
            return JsonResponse({
                'success': False,
                'message': '未选择任何产品或文件类型。'
            })
        
        # 创建压缩任务
        task = CompressionTask.objects.create(
            product_ids=product_ids_str,
            file_type=file_type,
            status='pending',
            progress=0,
            user_id=request.user.id
        )
        
        # 启动异步压缩处理
        from .tasks import process_compression_task
        import threading
        threading.Thread(target=process_compression_task, args=(task.task_id,), daemon=True).start()
        
        return JsonResponse({
            'success': True,
            'task_id': str(task.task_id),
            'message': '压缩任务已开始'
        })
    
    return JsonResponse({
        'success': False,
        'message': '无效的请求方法'
    })


@login_required
def check_compression_progress(request):
    """检查压缩进度"""
    task_id = request.GET.get('task_id')
    if not task_id:
        return JsonResponse({
            'success': False,
            'message': '缺少任务ID'
        })
    
    try:
        task = CompressionTask.objects.get(task_id=task_id)
        return JsonResponse({
            'success': True,
            'progress': task.progress,
            'status': task.status,
            'is_completed': task.status == 'completed',
            'error_message': task.error_message
        })
    except CompressionTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'检查进度失败: {str(e)}'
        })


@login_required
def download_compressed_file(request):
    """下载压缩文件"""
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        file_type = request.POST.get('file_type')
        
        if not task_id:
            return JsonResponse({
                'success': False,
                'message': '缺少任务ID'
            })
        
        try:
            task = CompressionTask.objects.get(task_id=task_id)
            
            if task.status != 'completed':
                return JsonResponse({
                    'success': False,
                    'message': '压缩任务尚未完成'
                })
            
            if not task.compressed_file_path:
                return JsonResponse({
                    'success': False,
                    'message': '压缩文件不存在'
                })
            
            # 检查文件是否存在
            from pathlib import Path
            BASE_DIR = Path(__file__).resolve().parent.parent
            full_file_path = os.path.join(BASE_DIR, task.compressed_file_path)
            if not os.path.exists(full_file_path):
                return JsonResponse({
                    'success': False,
                    'message': '压缩文件不存在'
                })
            
            # 读取文件内容
            with open(full_file_path, 'rb') as f:
                file_content = f.read()
            
            # 设置响应头
            response = HttpResponse(file_content, content_type='application/zip')
            
            # 生成文件名（大写）
            if len(task.product_ids.split(',')) == 1:
                # 单个产品
                product = Product.objects.get(id=task.product_ids)
                if task.file_type in ['pdf', 'step', 'both']:
                    # 单个产品下载，使用产品图号+文件类型（不使用实际文件名）
                    zip_filename = f"{product.drawing_no_1}_{task.file_type}.zip".upper()
            else:
                # 多个产品，使用带时间戳的名称
                ts = task.updated_at.strftime('%Y%m%d_%H%M%S')
                zip_filename = f"batch_download_{task.file_type}_{ts}.zip".upper()
            
            # 移除文件名中的_BOTH（根据需求，批量下载PDF和STEP不需要显示BOTH）
            zip_filename = zip_filename.replace('_BOTH', '')
            
            # 计算文件大小（必须在使用前定义）
            file_size_mb = os.path.getsize(full_file_path) / (1024 * 1024)
            
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            
            # 记录下载日志，使用与profile视图兼容的格式
            from .models import Log
            # 判断是单个下载还是批量下载
            is_single_download = len(task.product_ids.split(',')) == 1
            action_type = 'single_download' if is_single_download else 'batch_download'
            
            # 格式化日志详情，区分单个和批量下载
            if is_single_download:
                # 单个下载格式
                details = f'Product ID: {task.product_ids}, File Type: {task.file_type}, Total Size: {file_size_mb:.2f} MB, Async Task ID: {task_id}'
            else:
                # 批量下载格式
                details = f'Product IDs: {task.product_ids}, File Type: {task.file_type}, Total Size: {file_size_mb:.2f} MB, Async Task ID: {task_id}'
            
            Log.objects.create(
                user=request.user,
                action_type=action_type,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details=details
            )
            
            # 记录下载统计
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            user_profile.record_download(file_size_mb)
            
            return response
            
        except CompressionTask.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '任务不存在'
            })
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '产品不存在'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'下载失败: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': '无效的请求方法'
    })


@login_required
def check_batch_file_size(request):
    """检查批量下载文件大小（与现有功能兼容）"""
    if request.method == 'POST':
        # Handle both form data and JSON requests
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            product_ids_str = data.get('product_ids', '')
            file_type = data.get('file_type', '')
        else:
            product_ids_str = request.POST.get('product_ids', '')
            file_type = request.POST.get('file_type', '')
        
        product_ids = [int(pid) for pid in product_ids_str.split(',') if pid.strip().isdigit()]

        if not product_ids or not file_type:
            return JsonResponse({
                'can_download': False,
                'message': '未选择任何产品或文件类型。'
            })

        products = Product.objects.filter(id__in=product_ids)
        total_size_mb = 0
        missing_files = []

        for product in products:
            file_path = None
            if file_type == 'pdf':
                file_path = product.pdf_file_path
            elif file_type == 'step':
                file_path = product.step_file_path
            elif file_type == 'bmp':
                file_path = product.bmp_file_path
            elif file_type == 'both':
                # 对于'both'类型，检查PDF和STEP文件大小
                if product.pdf_file_path:
                    full_pdf_path = os.path.join(settings.MEDIA_ROOT, str(product.pdf_file_path).replace('media/', ''))
                    if os.path.exists(full_pdf_path):
                        total_size_mb += os.path.getsize(full_pdf_path) / (1024 * 1024)
                    else:
                        missing_files.append(os.path.basename(str(product.pdf_file_path)))
                if product.step_file_path:
                    full_step_path = os.path.join(settings.MEDIA_ROOT, str(product.step_file_path).replace('media/', ''))
                    if os.path.exists(full_step_path):
                        total_size_mb += os.path.getsize(full_step_path) / (1024 * 1024)
                    else:
                        missing_files.append(os.path.basename(str(product.step_file_path)))
                continue # 跳过下面的通用文件处理逻辑
            
            if file_path:
                relative_path = str(file_path)
                if relative_path.startswith('media/'):
                    relative_path = relative_path[len('media/'):]
                elif relative_path.startswith('/media/'):
                    relative_path = relative_path[len('/media/'):]
                
                full_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                
                if os.path.exists(full_file_path):
                    file_size_bytes = os.path.getsize(full_file_path)
                    total_size_mb += file_size_bytes / (1024 * 1024)
                else:
                    missing_files.append(os.path.basename(file_path))
            else:
                missing_files.append(f"产品 {product.description} 没有关联的 {file_type} 文件")
        
        # 优先使用前端传递的language参数，其次通过HTTP_REFERER判断
        # 从不同位置获取language参数，包括JSON请求体
        language_param = None
        if request.content_type == 'application/json':
            language_param = data.get('language')
        if not language_param:
            language_param = request.POST.get('language') or request.GET.get('language')
        
        is_english = language_param == 'en'
        if not is_english:
            referer = request.META.get('HTTP_REFERER', '')
            is_english = 'en/' in referer or '_en/' in referer or 'search_results_en' in referer or 'product_detail_en' in referer
        # Check if there are any missing files
        if missing_files:
            if is_english:
                message = f"Missing files: {', '.join(missing_files)}"
            else:
                message = f"缺失文件: {', '.join(missing_files)}"
            response_data = {
                'can_download': False,
                'message': message,
                'total_size_mb': round(total_size_mb, 2),
                'missing_files': missing_files
            }
        else:
            # If no missing files, check download permissions
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            can_download, message = user_profile.can_download_file(total_size_mb, is_batch=True, is_english=is_english)

            response_data = {
                'can_download': can_download,
                'message': message,
                'total_size_mb': round(total_size_mb, 2),
                'missing_files': missing_files
            }
        return JsonResponse(response_data)
    return JsonResponse({'can_download': False, 'message': '无效的请求方法。'})