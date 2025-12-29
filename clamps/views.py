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



import io
import os
import re
import secrets
import string
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 第三方库
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import chardet
import csv
import glob

# Django核心
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt

# 本地应用
from .models import Product
from .pdf_utils import PDFProcessor



def create_watermark(watermark_text, output_path):
    # 将页面尺寸设置为A4横向
    pagesize_landscape_a4 = landscape(A4)
    c = canvas.Canvas(output_path, pagesize=pagesize_landscape_a4)

    # 水印内容拆分为两行
    # 假设 watermark_text 格式为 "For Reference Only[OBARA] {username} {datetime}"
    # 第一行："For Reference Only[OBARA]"
    # 第二行："{username} {datetime}"
    if '[OBARA]' in watermark_text:
        prefix, suffix = watermark_text.split('[OBARA]', 1)
        line1 = prefix.strip() + '[OBARA]'
        line2 = suffix.strip()
    else:
        line1 = watermark_text
        line2 = ''

    # 调整字体大小和透明度
    font_size = 18  # 调整字体大小以合理填充纸张，减小
    c.setFillColor(Color(1, 0, 0, alpha=0.3))  # 红色，颜色改为红色
    c.setFont("Helvetica-Bold", font_size)

    # 旋转水印
    c.rotate(30)  # 调整旋转角度

    # 获取页面尺寸
    page_width, page_height = pagesize_landscape_a4

    # 计算水印的重复间隔和起始位置
    # 假设每行水印的宽度和高度
    line1_width = c.stringWidth(line1, "Helvetica-Bold", font_size)
    line2_width = c.stringWidth(line2, "Helvetica-Bold", font_size)
    max_line_width = max(line1_width, line2_width)
    line_height = font_size * 2  # 行高，略大于字体大小

    # 调整循环范围和步长，使水印合理填充整个纸张
    # 增加水印密度，调整x和y的步长
    x_step = max_line_width * 1.5 # 调整x方向的步长
    y_step = line_height * 4.5 # 调整y方向的步长

    # 调整起始位置，确保水印覆盖整个页面
    start_x = -page_width / 2
    start_y = -page_height / 2

    for x in range(int(start_x), int(page_width * 1.5), int(x_step)):
        for y in range(int(start_y), int(page_height * 1.5), int(y_step)):
            c.drawString(x, y, line1)
            c.drawString(x, y - line_height, line2) # 第二行在第一行下方

    c.save()


def add_watermark_to_pdf(input_pdf_path, output_pdf_path, watermark_text):
    watermark_buffer = io.BytesIO()
    create_watermark(watermark_text, watermark_buffer)
    watermark_buffer.seek(0)
    watermark_pdf = PdfReader(watermark_buffer)
    watermark_page = watermark_pdf.pages[0]
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    for i in range(len(reader.pages)):
        page = reader.pages[i]
        page.merge_page(watermark_page)
        writer.add_page(page)
    with open(output_pdf_path, "wb") as output_file:
        writer.write(output_file)



from .models import Category, Log, UserProfile, StyleLink, UserFeedback, UserStyleLinkVisit


def is_superuser(user):
    return user.is_superuser


def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser


def home(request):
    return render(request, 'home.html')


def home_en(request):
    return render(request, 'home_en.html')



def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # 优化：使用get_or_create减少数据库查询次数
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            
            if user_profile.is_password_expired():
                logout(request)
                messages.error(request, '您的账户密码已过期，请联系您的营业经理进行账号续期。')
                return render(request, 'login.html')

            # 优化：使用事务批量处理数据库操作
            from django.db import transaction
            with transaction.atomic():
                # 记录登录日志
                Log.objects.create(
                    user=user, 
                    action_type='login', 
                    ip_address=request.META.get('REMOTE_ADDR'), 
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # 检查是否有已处理但未通知的反馈
                processed_feedback = UserFeedback.objects.filter(
                    user=user,
                    status__in=['已处理', '无法确认', '无效反馈'],
                    is_notified=False
                )
                
                if processed_feedback.exists():
                    messages.success(request, '您提交的反馈已被管理员处理，感谢您的反馈。')
                    # 标记所有已处理的反馈为已通知
                    processed_feedback.update(is_notified=True)
            
            # 处理next参数，重定向到原来请求的页面
            next_url = request.GET.get('next', request.POST.get('next', 'clamps:home'))
            return redirect(next_url)
        else:
            messages.error(request, '无效的用户名或密码，请联系您的营业经理重新获取用户名或进行密码重置。')
            return render(request, 'login.html')
    return render(request, 'login.html')


def user_login_en(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # 优化：使用get_or_create减少数据库查询次数
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            
            if user_profile.is_password_expired():
                logout(request)
                messages.error(request, 'Your account password has expired. Please contact your sales manager for account renewal.')
                return render(request, 'login_en.html')
            
            # 优化：使用事务批量处理数据库操作
            from django.db import transaction
            with transaction.atomic():
                # 记录登录日志
                Log.objects.create(
                    user=user, 
                    action_type='login', 
                    ip_address=request.META.get('REMOTE_ADDR'), 
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # 检查是否有已处理但未通知的反馈
                processed_feedback = UserFeedback.objects.filter(
                    user=user,
                    status__in=['已处理', '无法确认', '无效反馈'],
                    is_notified=False
                )
                
                if processed_feedback.exists():
                    messages.success(request, 'Your feedback has been processed by the administrator. Thank you for your feedback.')
                    # 标记所有已处理的反馈为已通知
                    processed_feedback.update(is_notified=True)
            
            # 处理next参数，重定向到原来请求的页面
            next_url = request.GET.get('next', request.POST.get('next', 'clamps:home_en'))
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password. Please contact your business manager to obtain a new username or reset your password.')
            return render(request, 'login_en.html')
    return render(request, 'login_en.html')



def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for i in range(length))
    return password


@login_required
def user_logout(request):
    Log.objects.create(
        user=request.user, 
        action_type='logout', 
        ip_address=request.META.get('REMOTE_ADDR'), 
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    logout(request)
    messages.info(request, '您已成功登出。')
    return redirect('clamps:login')


@login_required
def user_logout_en(request):
    Log.objects.create(
        user=request.user, 
        action_type='logout', 
        ip_address=request.META.get('REMOTE_ADDR'), 
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('clamps:login_en')



@login_required
def search(request):
    categories = Category.objects.all()
    return render(request, 'search.html', {'categories': categories})


@login_required
def search_en(request):
    categories = Category.objects.all()
    return render(request, 'search_en.html', {'categories': categories})



@login_required
def search_results_base(request, template_name):
    query_params = request.GET.copy()
    category_id = query_params.get('category')
    description = query_params.get('description')
    drawing_no_1 = query_params.get('drawing_no_1')
    sub_category_type = query_params.get('sub_category_type')
    
    # 创建缓存键，基于搜索参数
    cache_key = f'search_results_{hash(frozenset(query_params.items()))}'
    
    # 检查缓存是否存在
    cached_context = cache.get(cache_key)
    if cached_context:
        # 如果是英文页面，确保使用正确的模板
        if template_name == 'search_results_en.html':
            return render(request, template_name, cached_context)
        return render(request, template_name, cached_context)

    # 数值范围参数
    stroke = query_params.get('stroke')
    clamping_force = query_params.get('clamping_force')
    weight = query_params.get('weight')
    throat_depth = query_params.get('throat_depth')
    throat_width = query_params.get('throat_width')

    transformer = query_params.get('transformer')
    electrode_arm_end = query_params.get('electrode_arm_end')
    motor_manufacturer = query_params.get('motor_manufacturer')
    has_balance = query_params.get('has_balance')
    
    # 新增的四个字段
    transformer_placement = query_params.get('transformer_placement')
    flange_pcd = query_params.get('flange_pcd')
    bracket_direction = query_params.get('bracket_direction')
    water_circuit = query_params.get('water_circuit')
    gearbox_type = query_params.get('gearbox_type')

    # 获取排序参数
    sort_by = request.GET.get('sort_by', 'drawing_no_1')
    # 获取排序方向，默认为升序
    sort_dir = request.GET.get('sort_dir', 'asc')
    
    # 构建排序表达式
    if sort_dir == 'desc':
        order_by = f'-{sort_by}'
    else:
        order_by = sort_by
    
    # 使用Q对象构建复杂查询条件，减少数据库查询次数
    q_objects = Q()
    
    if category_id:
        try:
            # 尝试将category_id转换为整数，使用category_id过滤
            q_objects &= Q(category_id=int(category_id))
        except ValueError:
            # 如果转换失败，说明是分类名称，使用category__name过滤
            q_objects &= Q(category__name=category_id)
    if description:
        description_keywords = [keyword.strip() for keyword in description.split() if keyword.strip()]
        if description_keywords:
            description_q = Q()
            for keyword in description_keywords:
                description_q |= Q(description__icontains=keyword)
            q_objects &= description_q
    if drawing_no_1:
        drawing_numbers = [num.strip() for num in drawing_no_1.split(',') if num.strip()]
        if drawing_numbers:
            drawing_q = Q()
            for num in drawing_numbers:
                drawing_q |= Q(drawing_no_1__icontains=num)
            q_objects &= drawing_q
    if sub_category_type:
        q_objects &= Q(sub_category_type__icontains=sub_category_type)

    # 处理数值范围查询 - 返回Q对象
    def build_range_q(field_name, query_string):
        range_q = Q()
        if query_string:
            query_string = query_string.strip()
            if '~' in query_string:
                parts = query_string.split('~')
                min_val_str = parts[0].strip()
                max_val_str = parts[1].strip()

                if min_val_str:
                    try:
                        min_val = float(min_val_str)
                        range_q &= Q(**{f'{field_name}__gte': min_val})
                    except ValueError:
                        pass # 忽略无效的最小值
                if max_val_str:
                    try:
                        max_val = float(max_val_str)
                        range_q &= Q(**{f'{field_name}__lte': max_val})
                    except ValueError:
                        pass # 忽略无效的最大值
            else:
                # 精确匹配
                try:
                    exact_val = float(query_string)
                    range_q &= Q(**{field_name: exact_val})
                except ValueError:
                    pass # 忽略无效的精确值
        return range_q

    # 添加数值范围查询
    q_objects &= build_range_q('stroke', stroke)
    q_objects &= build_range_q('clamping_force', clamping_force)
    q_objects &= build_range_q('weight', weight)
    q_objects &= build_range_q('throat_depth', throat_depth)
    q_objects &= build_range_q('throat_width', throat_width)

    # 添加其他字段查询
    if transformer:
        q_objects &= Q(transformer__icontains=transformer)
    if electrode_arm_end:
        q_objects &= Q(electrode_arm_end__icontains=electrode_arm_end)
    if motor_manufacturer:
        q_objects &= Q(motor_manufacturer__icontains=motor_manufacturer)
    if has_balance:
        # 处理中英文版本的has_balance值
        if has_balance in ['有', 'Yes']:
            q_objects &= Q(has_balance=True)
        elif has_balance in ['无', 'No']:
            q_objects &= Q(has_balance=False)
    
    if gearbox_type:
        q_objects &= Q(gearbox_type__icontains=gearbox_type)
    
    if transformer_placement:
        q_objects &= Q(transformer_placement__icontains=transformer_placement)
    if flange_pcd:
        q_objects &= Q(flange_pcd__icontains=flange_pcd)
    if bracket_direction:
        q_objects &= Q(bracket_direction__icontains=bracket_direction)
    if water_circuit:
        q_objects &= Q(water_circuit__icontains=water_circuit)

    # 处理动态字段 (确保 transformer_placement 等已处理的字段不再被动态处理)
    dynamic_fields = {}
    for key, value in query_params.items():
        if key not in ["category", "description", "drawing_no_1", "sub_category_type",
                       "stroke", "clamping_force", "weight", "throat_depth", "throat_width",
                       "transformer", "electrode_arm_end", "motor_manufacturer", "has_balance",
                       "transformer_placement", "flange_pcd", "bracket_direction", "water_circuit",
                       "page", "csrfmiddlewaretoken", "ide_webview_request_time"] and value:
            dynamic_fields[key] = value

    for field_name, field_value in dynamic_fields.items():
        # 确保字段存在于Product模型中
        if hasattr(Product, field_name):
            # 动态字段支持范围搜索
            q_objects &= build_range_q(field_name, field_value)
    
    # 执行一次性查询
    queryset = Product.objects.filter(q_objects).order_by(order_by)

    # 记录搜索日志
    # 将QueryDict转换为更易读的格式，排除csrfmiddlewaretoken
    clean_params = {k: v[0] if len(v) == 1 else v for k, v in query_params.lists() if k != 'csrfmiddlewaretoken'}
    log_entry = Log(user=request.user, action_type='search', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=str(clean_params))
    log_entry.save()

    paginator = Paginator(queryset, 20)  # 每页20条记录
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 添加排序相关上下文
    context = {
        'page_obj': page_obj,
        'total_results': paginator.count,
        'query_params': query_params,
        'is_style_search': request.session.get('from_style_search', False),
        'sort_by': sort_by,
        'sort_dir': sort_dir
    }
    
    # 缓存搜索结果10分钟
    cache.set(cache_key, context, timeout=600)
    
    return render(request, template_name, context)

@login_required
def search_results(request):
    return search_results_base(request, 'search_results.html')


@login_required
def search_results_en(request):
    return search_results_base(request, 'search_results_en.html')



@login_required
def product_detail(request, product_id):
    # 缓存键，包含产品ID和语言
    cache_key = f'product_detail_{product_id}_zh'
    
    # 尝试从缓存获取
    cached_product = cache.get(cache_key)
    if cached_product:
        product = cached_product
    else:
        # 从数据库获取
        product = get_object_or_404(Product, id=product_id)
        # 缓存1小时
        cache.set(cache_key, product, timeout=3600)
    
    # 记录查看详情日志
    log_entry = Log(user=request.user, action_type='view', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Drawing No.: {product.drawing_no_1}')
    log_entry.save()
    return render(request, 'product_detail.html', {
        'product': product,
        'is_style_search': request.session.get('from_style_search', False)
    })


@login_required
def product_detail_en(request, product_id):
    # 缓存键，包含产品ID和语言
    cache_key = f'product_detail_{product_id}_en'
    
    # 尝试从缓存获取
    cached_product = cache.get(cache_key)
    if cached_product:
        product = cached_product
    else:
        # 从数据库获取
        product = get_object_or_404(Product, id=product_id)
        # 缓存1小时
        cache.set(cache_key, product, timeout=3600)
    
    # 记录查看详情日志
    log_entry = Log(user=request.user, action_type='view', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Drawing No.: {product.drawing_no_1} (English)')
    log_entry.save()
    return render(request, 'product_detail_en.html', {
        'product': product,
        'is_style_search': request.session.get('from_style_search', False)
    })





# 新增：检查文件大小的API端点
@login_required
def check_file_size(request, product_id, file_type):
    """检查文件大小是否满足下载条件"""
    # 优先使用前端传递的language参数，其次通过HTTP_REFERER判断
    is_english = request.GET.get('language') == 'en' or request.POST.get('language') == 'en'
    if not is_english:
        referer = request.META.get('HTTP_REFERER', '')
        is_english = 'en/' in referer or '_en/' in referer or 'search_results_en' in referer or 'product_detail_en' in referer
    
    try:
        product = get_object_or_404(Product, id=product_id)
        file_path = None
        
        if file_type == 'pdf':
            file_path = product.pdf_file_path
        elif file_type == 'step':
            file_path = product.step_file_path
        elif file_type == 'bmp':
            file_path = product.bmp_file_path
        
        if not file_path:
            return JsonResponse({
                'can_download': False,
                'message': f'Product {product.drawing_no_1} has no associated {file_type} file' if is_english else f'产品 {product.drawing_no_1} 没有关联的 {file_type} 文件'
            })

        # 处理路径前缀，确保是相对于 MEDIA_ROOT 的路径
        relative_path = str(file_path)
        if relative_path.startswith('media/'):
            relative_path = relative_path[len('media/'):]
        elif relative_path.startswith('/media/'):
            relative_path = relative_path[len('/media/'):]

        full_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        
        if not os.path.exists(full_file_path):
            return JsonResponse({
                'can_download': False,
                'message': f'{file_type.upper()} file does not exist or is corrupted' if is_english else f'{file_type.upper()} 文件不存在或已损坏'
            })
        
        # 获取文件大小（MB）
        file_size_bytes = os.path.getsize(full_file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # 获取或创建用户配置
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # 检查下载限制
        can_download, message = user_profile.can_download_file(file_size_mb, is_english=is_english)
        
        return JsonResponse({
            'can_download': can_download,
            'message': message,
            'file_size_mb': round(file_size_mb, 2)
        })
        
    except Exception as e:
        return JsonResponse({
            'can_download': False,
            'message': f'Error checking file: {str(e)}' if is_english else f'检查文件时发生错误: {str(e)}'
        })



@login_required
def download_file(request, product_id, file_type):
    product = get_object_or_404(Product, id=product_id) # 使用 get_object_or_404 避免 Product.DoesNotExist 错误
    file_path = None
    original_filename = None
    
    if file_type == 'pdf':
        file_path = product.pdf_file_path
    elif file_type == 'step':
        file_path = product.step_file_path
    elif file_type == 'bmp':
        file_path = product.bmp_file_path

    if file_path:
        # 处理路径前缀，确保是相对于 MEDIA_ROOT 的路径
        relative_path = str(file_path) # 确保是字符串
        if relative_path.startswith('media/'):
            relative_path = relative_path[len('media/'):]
        elif relative_path.startswith('/media/'):
            relative_path = relative_path[len('/media/'):]

        full_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        
        if os.path.exists(full_file_path):
            # 获取文件大小（MB）
            file_size_bytes = os.path.getsize(full_file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            # 获取或创建用户配置
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # 检查下载限制
            can_download, message = user_profile.can_download_file(file_size_mb)
            if not can_download:
                messages.error(request, f"下载失败：{message}")
                
                referer = request.META.get('HTTP_REFERER')
                current_site = request.get_host()  # 用于域名校验

                if referer:
                    from urllib.parse import urlparse
                    parsed_referer = urlparse(referer)
                    
                    # 确保是同站来源，防止开放重定向
                    if parsed_referer.netloc == current_site:
                        path = parsed_referer.path  # 例如: /product/123_en/

                        # 判断是否来自搜索结果页
                        if 'search_results' in path:
                            return redirect(referer)
                        
                        # 判断是否来自英文产品详情页，匹配 /product/数字_en/ 模式
                        import re
                        if re.match(r'^/product/\d+_en/$', path):
                            return redirect(referer)

                # 默认返回中文产品详情页
                return redirect('clamps:product_detail', product_id=product_id)
            
            # 获取原始文件名（不带路径）
            original_filename = os.path.basename(file_path)
            
            # 将原始文件名的后缀改为大写
            base_name, ext = os.path.splitext(original_filename)
            original_filename_with_uppercase_ext = f"{base_name}{ext.upper()}"
            
            # 对于bmp, pdf, step文件，进行压缩
            if file_type in ['bmp', 'pdf', 'step']:
                # 获取不带后缀的文件名，并去除特定后缀
                base_name, ext = os.path.splitext(original_filename_with_uppercase_ext)
                if file_type == 'pdf' and base_name.lower().endswith(('_pdf','_pdf')):
                    base_name = base_name
                elif file_type == 'step' and base_name.endswith('_STEP'):
                    base_name = base_name
                elif file_type == 'bmp' and base_name.endswith('_BMP'):
                    base_name = base_name
                else:
                    # 如果没有特定后缀，则直接使用原始文件名
                    pass
                
                # 生成水印文本
                temp_watermarked_pdf_path = None
                if file_type == 'pdf':
                    # 生成水印文本
                    watermark_text = f"For Reference Only[OBARA] {request.user.username} {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')}"
                    temp_watermarked_pdf_path = os.path.join(tempfile.gettempdir(), f"watermarked_{original_filename}")
                    PDFProcessor.add_watermark(full_file_path, temp_watermarked_pdf_path, watermark_text)
                    final_file_path = temp_watermarked_pdf_path
                else:
                    final_file_path = full_file_path
                    
                # 定义流式生成zip文件的函数
                def zip_generator():
                    # 使用BytesIO作为zip文件的容器
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                        # 添加文件到zip
                        zf.write(final_file_path, arcname=original_filename_with_uppercase_ext)
                    
                    # 清理临时文件
                    if temp_watermarked_pdf_path and os.path.exists(temp_watermarked_pdf_path):
                        os.remove(temp_watermarked_pdf_path)
                    
                    # 重置buffer位置
                    zip_buffer.seek(0)
                    
                    # 分块读取并返回数据
                    while True:
                        chunk = zip_buffer.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        yield chunk
                
                # 创建StreamingHttpResponse
                response = StreamingHttpResponse(zip_generator(), content_type='application/zip')
                
                # 根据filename_format参数决定下载文件名格式
                filename_format = request.GET.get('filename_format', '')
                if filename_format == 'with_type':
                    # 使用 "文件名_文件类型" 格式，文件类型大写
                    zip_filename = f"{base_name}_{file_type.upper()}.zip"
                else:
                    # 默认格式
                    zip_filename = f"{base_name}.zip"
                
                response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
                
                # 记录下载日志
                log_entry = Log(user=request.user, action_type='download', ip_address=request.META.get('REMOTE_ADDR'),
                                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                                details=f'Drawing No.: {product.drawing_no_1}, File Type: {file_type}, File Size: {file_size_mb:.2f} MB')
                log_entry.save()
                
                # 记录下载统计
                user_profile.record_download(file_size_mb)
                
                return response
            else:
                # 对于其他文件类型，重定向到受保护的媒体URL
                # 记录下载日志
                log_entry = Log(user=request.user, action_type='download', ip_address=request.META.get('REMOTE_ADDR'),
                                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                                details=f'Drawing No.: {product.drawing_no_1}, File Type: {file_type}, File Size: {file_size_mb:.2f} MB')
                log_entry.save()
                
                # 记录下载统计
                user_profile.record_download(file_size_mb)
                
                return redirect('clamps:protected_media', path=relative_path)

        else:
            messages.error(request, f"{file_type.upper()} 文件不存在或已损坏")
            referer = request.META.get('HTTP_REFERER')
            if referer and 'search_results' in referer:
                return redirect(referer)
            else:
                return redirect('clamps:product_detail', product_id=product_id)
    else:
        messages.error(request, f"产品没有关联的 {file_type} 文件")
        referer = request.META.get('HTTP_REFERER')
        if referer and 'search_results' in referer:
            return redirect(referer)
        else:
            return redirect('clamps:product_detail', product_id=product_id)



@login_required
def batch_download_view(request, file_type):
    if request.method == 'POST':
        product_ids_str = request.POST.get('product_ids', '')
        product_ids = [int(pid) for pid in product_ids_str.split(',') if pid.strip().isdigit()]
        
        if not product_ids:
            messages.error(request, "未选择任何产品进行批量下载。")
            return redirect(request.META.get('HTTP_REFERER', 'clamps:home'))

        products = Product.objects.filter(id__in=product_ids)
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            total_size_mb = 0
            files_to_add = []

            for product in products:
                file_path = None
                if file_type == 'pdf':
                    file_path = product.pdf_file_path
                elif file_type == 'step':
                    file_path = product.step_file_path
                elif file_type == 'bmp':
                    file_path = product.bmp_file_path
                elif file_type == 'both':
                    # 对于'both'类型，尝试下载PDF和STEP文件
                    if product.pdf_file_path:
                        full_pdf_path = os.path.join(settings.MEDIA_ROOT, str(product.pdf_file_path).replace('media/', ''))
                        if os.path.exists(full_pdf_path):
                            # 将PDF文件名的后缀改为大写
                            pdf_arcname = os.path.basename(str(product.pdf_file_path))
                            pdf_base, pdf_ext = os.path.splitext(pdf_arcname)
                            pdf_arcname_with_uppercase_ext = f"{pdf_base}{pdf_ext.upper()}"
                            files_to_add.append((full_pdf_path, pdf_arcname_with_uppercase_ext))
                            total_size_mb += os.path.getsize(full_pdf_path) / (1024 * 1024)
                        else:
                            messages.warning(request, f"文件 {os.path.basename(str(product.pdf_file_path))} 不存在或已损坏，已跳过。")
                    if product.step_file_path:
                        full_step_path = os.path.join(settings.MEDIA_ROOT, str(product.step_file_path).replace('media/', ''))
                        if os.path.exists(full_step_path):
                            # 将STEP文件名的后缀改为大写
                            step_arcname = os.path.basename(str(product.step_file_path))
                            step_base, step_ext = os.path.splitext(step_arcname)
                            step_arcname_with_uppercase_ext = f"{step_base}{step_ext.upper()}"
                            files_to_add.append((full_step_path, step_arcname_with_uppercase_ext))
                            total_size_mb += os.path.getsize(full_step_path) / (1024 * 1024)
                        else:
                            messages.warning(request, f"文件 {os.path.basename(str(product.step_file_path))} 不存在或已损坏，已跳过。")
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
                        # 将文件名的后缀改为大写
                        arcname = os.path.basename(file_path)
                        base, ext = os.path.splitext(arcname)
                        arcname_with_uppercase_ext = f"{base}{ext.upper()}"
                        files_to_add.append((full_file_path, arcname_with_uppercase_ext))
                    else:
                        messages.warning(request, f"文件 {os.path.basename(file_path)} 不存在或已损坏，已跳过。")
                else:
                    messages.warning(request, f"产品 {product.description} 没有关联的 {file_type} 文件，已跳过。")
            
            # 由于前端已经通过checkBatchFileSize检查了文件大小，这里不再重复检查
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)

            for full_path, arcname in files_to_add:
                if file_type == 'pdf' or (file_type == 'both' and arcname.lower().endswith('.pdf')):
                    watermark_text = f"For Reference Only[OBARA] {request.user.username} {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')}"
                    temp_watermarked_pdf_path = os.path.join(tempfile.gettempdir(), f"watermarked_{arcname}")
                    PDFProcessor.add_watermark(full_path, temp_watermarked_pdf_path, watermark_text)
                    zf.write(temp_watermarked_pdf_path, arcname=arcname)
                    os.remove(temp_watermarked_pdf_path)
                else:
                    zf.write(full_path, arcname=arcname)


        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        
        # 检查是否是单个产品批量下载
        is_single_product = len(product_ids) == 1
        if is_single_product:
            # 单个产品批量下载，使用产品图号作为压缩包名称
            product = products.first()
            zip_filename = f"{product.drawing_no_1}.zip"
        else:
            # 多个产品批量下载，使用带时间戳的批量下载名称
            ts = timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')
            zip_filename = f"batch_download_{file_type}_{ts}.zip"
        
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        # 获取所有产品的图号
        drawing_nos = [product.drawing_no_1 for product in products if product.drawing_no_1]
        drawing_nos_str = ', '.join(drawing_nos)
        
        # 记录批量下载日志
        log_entry = Log(user=request.user, action_type='batch_download', ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        details=f'File Type: {file_type}, Drawing Nos: {drawing_nos_str}, Total Size: {total_size_mb:.2f} MB')
        log_entry.save()
        
        # 记录批量下载统计 - 增加实际下载的文件数量
        # 对于'both'类型，每个产品下载2个文件，否则每个产品下载1个文件
        file_count = len(products) if file_type != 'both' else len(products) * 2
        # 记录下载大小
        user_profile.daily_download_size_mb += total_size_mb
        # 增加文件数量统计
        user_profile.daily_download_count += file_count
        user_profile.last_download_date = timezone.localtime(timezone.now()).date()
        user_profile.save()
        
        return response
    messages.error(request, "无效的批量下载请求。")
    return redirect(request.META.get('HTTP_REFERER', 'clamps:home'))



@login_required
def check_batch_file_size(request):
    if request.method == 'POST':
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
        is_english = request.POST.get('language') == 'en' or request.GET.get('language') == 'en'
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



@login_required
@user_passes_test(is_staff_or_superuser)
def management_dashboard(request):
    total_products = Product.objects.count()
    total_users = User.objects.count()
    total_categories = Category.objects.count()
    recent_logs = Log.objects.order_by('-timestamp')[:10]
    
    context = {
        'total_products': total_products,
        'total_users': total_users,
        'total_categories': total_categories,
        'recent_logs': recent_logs,
    }
    return render(request, 'management/dashboard.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def manage_users(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_config':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            profile, created = UserProfile.objects.get_or_create(user=user)

            new_validity_days = int(request.POST.get('password_validity_days', 5))

            # ✅ 强制重置为今天，无论是否修改有效期
            profile.password_last_changed = timezone.now()
            profile.password_validity_days = new_validity_days
            profile.customer_name = request.POST.get('customer_name', '').strip()
            profile.max_single_download_mb = int(request.POST.get('max_single_download_mb', 100))
            profile.max_batch_download_mb = int(request.POST.get('max_batch_download_mb', 200))
            profile.max_daily_download_gb = int(request.POST.get('max_daily_download_gb', 100))
            profile.max_daily_download_count = int(request.POST.get('max_daily_download_count', 100))

            user.email = request.POST.get('email', '').strip()
            user.first_name = request.POST.get('password_remark', '').strip()
            user.save()
            profile.save()

            messages.success(request, f'用户 {user.username} 的配置已更新。')
            return redirect('clamps:manage_users')

        elif action == 'activate':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            user.is_active = True
            user.save()
            messages.success(request, f'用户 {user.username} 已激活。')
            return redirect('clamps:manage_users')

        elif action == 'set_password':
            user_id = request.POST.get('user_id')
            new_password = request.POST.get('new_password')
            password_remark = request.POST.get('password_remark')
            
            if not new_password or not password_remark:
                messages.error(request, '新密码和密码备注不能为空。')
                return redirect('clamps:manage_users')
            
            user = get_object_or_404(User, id=user_id)
            user.set_password(new_password)
            user.first_name = password_remark  # 将密码备注存储到first_name字段
            user.save()
            
            # 更新密码修改时间
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            user_profile.password_last_changed = timezone.now()
            user_profile.save()
            
            log_entry = Log(user=request.user, action_type='set_user_password', ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'User {user.username} password set manually')
            log_entry.save()
            
            messages.success(request, f'用户 {user.username} 的密码已成功设置。')
            return redirect('clamps:manage_users')

        elif action == 'deactivate':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, id=user_id)
            if user.is_superuser:
                messages.error(request, '不能停用超级管理员。')
            else:
                user.is_active = False
                user.save()
                messages.success(request, f'用户 {user.username} 已停用。')
            return redirect('clamps:manage_users')

    # GET 请求处理 - 根据权限过滤用户
    if request.user.is_superuser:
        # 超级管理员可以查看所有用户
        users = User.objects.all().order_by("username")
    else:
        # 一般管理员只能查看自己和自己创建的用户
        users = User.objects.filter(
            Q(id=request.user.id) | Q(profile__created_by=request.user)
        ).order_by("username")
    
    users_with_profiles = []

    active_users_count = 0
    admin_users_count = 0
    password_expired_count = 0

    for user in users:
        profile, created = UserProfile.objects.get_or_create(user=user)
        password_expired = profile.is_password_expired()
        password_expiry_date = profile.get_password_expiry_date()

        if user.is_active:
            active_users_count += 1
        if user.is_staff or user.is_superuser:
            admin_users_count += 1
        if password_expired:
            password_expired_count += 1

        users_with_profiles.append({
            "user": user,
            "profile": profile,
            "password_expired": password_expired,
            "password_expiry_date": password_expiry_date,
            "created_by": profile.created_by.username if profile.created_by else "N/A",
        })

    password_validity_choices = UserProfile.get_password_validity_choices()
    context = {
        "users_with_profiles": users_with_profiles,
        "password_validity_choices": password_validity_choices,
        "active_users_count": active_users_count,
        "admin_users_count": admin_users_count,
        "password_expired_count": password_expired_count,
    }
    return render(request, "management/users.html", context)

@login_required
@user_passes_test(is_staff_or_superuser)
def toggle_user_active(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    messages.success(request, f'用户 {user.username} 的状态已更新。')
    return redirect('clamps:manage_users')

@login_required
@user_passes_test(is_staff_or_superuser)
def reset_user_password(request, user_id):
    user = User.objects.get(id=user_id)
    new_password = generate_random_password()
    user.set_password(new_password)
    user.save()
    
    # 更新密码修改时间
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    user_profile.password_last_changed = timezone.now()
    user_profile.save()
    
    log_entry = Log(user=request.user, action_type='reset_user_password', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'User {user.username} password reset')
    log_entry.save()
    
    messages.success(request, f'用户 {user.username} 的新密码是: {new_password}')
    return redirect('clamps:manage_users')

@login_required
@user_passes_test(is_staff_or_superuser)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username # 保存用户名以便在消息中使用
        user.delete()
        messages.success(request, f'用户 {username} 已成功删除。')
        return redirect('clamps:manage_users')
    return render(request, 'management/delete_user_confirm.html', {'user': user})

@login_required
@user_passes_test(is_staff_or_superuser)
def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_remark = request.POST.get('password_remark')
        customer_name = request.POST.get('customer_name')
        
        if not username or not password or not password_remark or not customer_name:
            messages.error(request, '用户名、密码、密码备注和客户名称不能为空。')
            return redirect('clamps:manage_users')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, '该用户名已存在。')
            return redirect('clamps:manage_users')
            
        try:
            user = User.objects.create_user(username=username, password=password)
            user.is_staff = False  # 默认为普通用户
            user.is_superuser = False
            user.first_name = password_remark  # 将密码备注存储到first_name字段
            user.save()
            
            # 更新现有的UserProfile（由信号自动创建），设置默认密码有效期为5天，并保存客户名称
            profile = UserProfile.objects.get(user=user)
            profile.password_validity_days = 5
            profile.password_last_changed = timezone.now()
            profile.customer_name = customer_name
            profile.created_by = request.user
            profile.save()
            
            log_entry = Log(user=request.user, action_type='add_user', ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Added new user {username} with customer name {customer_name}')
            log_entry.save()
            messages.success(request, f'用户 {username} 添加成功。')
        except Exception as e:
            messages.error(request, f'添加用户失败: {e}')
            
        return redirect('clamps:manage_users')
    return redirect('clamps:manage_users')

@login_required
@user_passes_test(is_staff_or_superuser)
def export_users(request):
    # 记录导出数据日志
    Log.objects.create(
        user=request.user, 
        action_type='export_data', 
        details='导出用户信息数据',
        ip_address=request.META.get('REMOTE_ADDR'), 
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)
    writer.writerow(["用户名", "是否激活", "是否员工", "是否超级用户", "注册时间", "客户名称", "密码有效期（天）", "密码最后修改时间", "单次最大下载大小（MB）", "每日最大下载大小（GB）", "每日最大下载文件数", "单次批量下载最大大小（MB）", "创建者"])

    users = User.objects.all().order_by('username')
    # 获取项目配置的本地时区
    local_tz = timezone.get_current_timezone()
    
    for user in users:
        profile, created = UserProfile.objects.get_or_create(user=user)
        created_by_username = profile.created_by.username if profile.created_by else "N/A"
        
        # 转换注册时间为本地时区
        date_joined_local = user.date_joined.astimezone(local_tz)
        # 转换密码最后修改时间为本地时区（注意处理可能为None的情况）
        pwd_changed_local = profile.password_last_changed.astimezone(local_tz) if profile.password_last_changed else None
        
        writer.writerow([
            user.username, 
            user.is_active,
            user.is_staff, 
            user.is_superuser, 
            date_joined_local.strftime("%Y-%m-%d %H:%M:%S"),  # 本地时区时间
            profile.customer_name,
            profile.password_validity_days,
            pwd_changed_local.strftime("%Y-%m-%d %H:%M:%S") if pwd_changed_local else "N/A",  # 本地时区时间
            profile.max_single_download_mb,
            profile.max_daily_download_gb,
            profile.max_daily_download_count,
            profile.max_batch_download_mb,
            created_by_username
        ])
    return response

@login_required
@user_passes_test(is_staff_or_superuser)
def view_logs(request):
    logs = Log.objects.all()
    action_type = request.GET.get("action_type")
    username = request.GET.get("username")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    
    if action_type:
        if action_type == 'download':
            logs = logs.filter(action_type__in=['download', 'batch_download', 'single_download'])
        else:
            logs = logs.filter(action_type=action_type)
    if username:
        logs = logs.filter(user__username__icontains=username)
    if date_from:
        # 将naive datetime转换为带时区的datetime
        naive_date = datetime.strptime(date_from, '%Y-%m-%d')
        aware_date = timezone.make_aware(naive_date)
        logs = logs.filter(timestamp__gte=aware_date)
    if date_to:
        # 将naive datetime转换为带时区的datetime
        naive_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        aware_date = timezone.make_aware(naive_date)
        logs = logs.filter(timestamp__lte=aware_date)
    
    logs = logs.order_by("-timestamp")
    total_count = logs.count()
    login_count = logs.filter(action_type='login').count()
    search_count = logs.filter(action_type='search').count()
    download_count = logs.filter(action_type__in=['download', 'batch_download', 'single_download']).count()
    view_count = logs.filter(action_type='view').count()
    
    paginator = Paginator(logs, 20)  # 每页显示20条日志
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    # 获取所有用户名列表用于筛选
    usernames = Log.objects.values_list('user__username', flat=True).distinct().order_by('user__username')
    usernames = [username for username in usernames if username is not None]
    
    context = {
        "page_obj": page_obj,
        "total_count": total_count,
        "login_count": login_count,
        "search_count": search_count,
        "download_count": download_count,
        "view_count": view_count,
        "usernames": usernames,
    }
    return render(request, "management/logs.html", context)

@login_required
@user_passes_test(is_staff_or_superuser)
def export_data(request):
    if request.method == 'POST':
        data_type = request.POST.get('data_type')

        # -------------------- 导出产品 --------------------
        if data_type == 'products':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="products.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'ID', 'description', 'drawing_no_1', 'sub_category_type', 'stroke',
                'electrode_arm_end', 'clamping_force', 'electrode_arm_type',
                'transformer', 'weight', 'transformer_placement', 'flange_pcd',
                'bracket_direction', 'bracket_angle', 'motor_manufacturer',
                'bracket_count', 'gearbox_type', 'bracket_material',
                'gearbox_stroke', 'tool_changer', 'throat_depth', 'has_balance',
                'throat_width', 'water_circuit', 'grip_extension_length',
                'eccentricity', 'eccentricity_direction', 'eccentricity_to_center',
                'guidance_method', 'static_arm_eccentricity',
                'static_electrode_arm_end', 'moving_arm_eccentricity',
                'moving_electrode_arm_end', 'pivot_to_drive_center_dist',
                'static_arm_front_length', 'static_arm_front_height',
                'moving_arm_front_length', 'moving_arm_front_height',
                'pdf_file_path', 'step_file_path', 'bmp_file_path'
            ])
            products = Product.objects.all()
            for product in products:
                def yes_no(v):
                    return '有' if v else '无'
                def clean_path(path):
                    if not path:
                        return ''
                    return str(path).replace('media/', '', 1)
                writer.writerow([
                    product.id,
                    product.description or '',
                    product.drawing_no_1 or '',
                    product.sub_category_type or '',
                    product.stroke if product.stroke is not None else '',
                    product.electrode_arm_end or '',
                    product.clamping_force if product.clamping_force is not None else '',
                    product.electrode_arm_type or '',
                    product.transformer or '',
                    product.weight if product.weight is not None else '',
                    product.transformer_placement or '',
                    product.flange_pcd or '',
                    product.bracket_direction or '',
                    product.bracket_angle if product.bracket_angle is not None else '',
                    product.motor_manufacturer or '',
                    product.bracket_count if product.bracket_count is not None else '',
                    product.gearbox_type or '',
                    product.bracket_material or '',
                    product.gearbox_stroke or '',
                    product.tool_changer or '',
                    product.throat_depth if product.throat_depth is not None else '',
                    yes_no(product.has_balance),
                    product.throat_width if product.throat_width is not None else '',
                    product.water_circuit or '',
                    product.grip_extension_length if product.grip_extension_length is not None else '',
                    product.eccentricity if product.eccentricity is not None else '',
                    product.eccentricity_direction or '',
                    product.eccentricity_to_center or '',
                    product.guidance_method or '',
                    product.static_arm_eccentricity if product.static_arm_eccentricity is not None else '',
                    product.static_electrode_arm_end or '',
                    product.moving_arm_eccentricity if product.moving_arm_eccentricity is not None else '',
                    product.moving_electrode_arm_end or '',
                    product.pivot_to_drive_center_dist if product.pivot_to_drive_center_dist is not None else '',
                    product.static_arm_front_length if product.static_arm_front_length is not None else '',
                    product.static_arm_front_height if product.static_arm_front_height is not None else '',
                    product.moving_arm_front_length if product.moving_arm_front_length is not None else '',
                    product.moving_arm_front_height if product.moving_arm_front_height is not None else '',
                    clean_path(product.pdf_file_path),
                    clean_path(product.step_file_path),
                    clean_path(product.bmp_file_path)
                ])

            Log.objects.create(
                user=request.user,
                action_type='export_data',
                details='导出全部产品数据',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return response

        # -------------------- 导出日志 --------------------
        elif data_type == 'logs':
            # 复用 logs.html 的筛选参数
            action_type_filter = request.POST.get('action_type')
            username_filter  = request.POST.get('username')
            date_from_filter = request.POST.get('date_from')
            date_to_filter   = request.POST.get('date_to')

            logs = Log.objects.all()

            if action_type_filter:
                logs = logs.filter(action_type=action_type_filter)
            if username_filter:
                logs = logs.filter(user__username__icontains=username_filter)
            if date_from_filter:
                logs = logs.filter(timestamp__gte=date_from_filter)
            if date_to_filter:
                logs = logs.filter(timestamp__lte=date_to_filter + " 23:59:59")

            logs = logs.order_by("-timestamp")

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="logs.csv"'
            writer = csv.writer(response)
            writer.writerow(['Timestamp', 'User', 'Action Type', 'IP Address', 'User Agent', 'Details'])
            for log in logs:
                local_time = timezone.localtime(log.timestamp)
                writer.writerow([
                    local_time.strftime('%Y-%m-%d %H:%M:%S'),
                    log.user.username if log.user else 'N/A',
                    log.action_type,
                    log.ip_address,
                    log.user_agent,
                    log.details
                ])

            Log.objects.create(
                user=request.user,
                action_type='export_data',
                details='导出操作日志',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return response

    return render(request, 'management/export.html')

@login_required
@user_passes_test(is_staff_or_superuser)
def import_csv(request):
    import logging
    import time
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        start_time = time.time()
        csv_file = request.FILES['csv_file']

        # 1. 检查文件类型
        if not csv_file.name.lower().endswith('.csv'):
            messages.error(request, '请上传 CSV 文件。')
            return redirect('clamps:import_csv')

        # 2. 根据文件名提取分类
        try:
            category_name = os.path.splitext(csv_file.name)[0].strip()
            if not category_name:
                raise ValueError
        except Exception:
            messages.error(request, '无法从文件名提取分类名称。')
            return redirect('clamps:import_csv')

        category, _ = Category.objects.get_or_create(name=category_name)

        # 3. 编码检测（优化：使用流式读取，减少内存占用）
        # 先读取一小部分数据进行编码检测
        sample = csv_file.read(1024 * 1024)  # 读取1MB样本进行编码检测
        encoding = chardet.detect(sample)['encoding'] or 'utf-8'
        csv_file.seek(0)  # 重置文件指针到开头
        
        # 使用TextIOWrapper直接读取文件，避免一次性加载整个文件
        reader = csv.reader(io.TextIOWrapper(csv_file, encoding=encoding))
        try:
            next(reader)  # 跳过表头
        except StopIteration:
            messages.error(request, 'CSV 文件为空或没有标题行。')
            return redirect('clamps:import_csv')

        # 4. 预加载现有产品（优化：只查询需要的字段，减少内存占用）
        existing_products = {}
        # 使用values_list只获取drawing_no_1和id，避免加载整个对象
        for product in Product.objects.values_list('id', 'drawing_no_1'):
            product_id, drawing_no = product
            if drawing_no:
                existing_products[drawing_no.strip().upper()] = product_id

        products_to_create = []
        products_to_update = []
        created_count = updated_count = 0

        # 5. 解析并分组
        for i, row in enumerate(reader, start=2):
            if len(row) < 37:
                continue
            drawing_no_1 = row[1].strip()
            if not drawing_no_1:
                continue

            # 构造字段数据
            product_data = {
                'category': category,
                'description': row[0].strip(),
                'drawing_no_1': drawing_no_1,
                'sub_category_type': row[2].strip(),
                'stroke': float(row[3]) if row[3].strip() else None,
                'electrode_arm_end': row[4].strip(),
                'clamping_force': float(row[5]) if row[5].strip() else None,
                'electrode_arm_type': row[6].strip(),
                'transformer': row[7].strip(),
                'weight': float(row[8]) if row[8].strip() else None,
                'transformer_placement': row[9].strip(),
                'flange_pcd': row[10].strip(),
                'bracket_direction': row[11].strip(),
                'bracket_angle': float(row[12]) if row[12].strip() else None,
                'motor_manufacturer': row[13].strip(),
                'bracket_count': float(row[14]) if row[14].strip() else None,
                'gearbox_type': row[15].strip(),
                'bracket_material': row[16].strip(),
                'gearbox_stroke': row[17].strip(),
                'tool_changer': row[18].strip(),
                'throat_depth': float(row[19]) if row[19].strip() else None,
                'has_balance': row[20].strip() == '有',
                'throat_width': float(row[21]) if row[21].strip() else None,
                'water_circuit': row[22].strip(),
                'grip_extension_length': float(row[23]) if row[23].strip() else None,
                'eccentricity': float(row[24]) if row[24].strip() else None,
                'eccentricity_direction': row[25].strip(),
                'eccentricity_to_center': row[26].strip(),
                'guidance_method': row[27].strip(),
                'static_arm_eccentricity': float(row[28]) if row[28].strip() else None,
                'static_electrode_arm_end': row[29].strip(),
                'moving_arm_eccentricity': float(row[30]) if row[30].strip() else None,
                'moving_electrode_arm_end': row[31].strip(),
                'pivot_to_drive_center_dist': float(row[32]) if row[32].strip() else None,
                'static_arm_front_length': float(row[33]) if row[33].strip() else None,
                'static_arm_front_height': float(row[34]) if row[34].strip() else None,
                'moving_arm_front_length': float(row[35]) if row[35].strip() else None,
                'moving_arm_front_height': float(row[36]) if row[36].strip() else None,
                'pdf_file_path': os.path.join('media', row[37].strip()) if len(row) > 37 and row[37].strip() else '',
                'step_file_path': os.path.join('media', row[38].strip()) if len(row) > 38 and row[38].strip() else '',
                'bmp_file_path': os.path.join('media', row[39].strip()) if len(row) > 39 and row[39].strip() else '',
            }

            key = drawing_no_1.strip().upper()
            if key in existing_products:
                # 更新：构造Product对象，包含id和新数据
                product = Product(id=existing_products[key], **product_data)
                products_to_update.append(product)
                updated_count += 1
            else:
                # 新建
                products_to_create.append(Product(**product_data))
                created_count += 1

        # 6. 批量写入（优化：使用更大的批次大小）
        batch_size = 5000  # 增加批次大小，提高导入速度
        
        # 获取所有字段名，用于bulk_update
        all_fields = [
            'category', 'description', 'drawing_no_1', 'sub_category_type',
            'stroke', 'electrode_arm_end', 'clamping_force', 'electrode_arm_type',
            'transformer', 'weight', 'transformer_placement', 'flange_pcd',
            'bracket_direction', 'bracket_angle', 'motor_manufacturer', 'bracket_count',
            'gearbox_type', 'bracket_material', 'gearbox_stroke', 'tool_changer',
            'throat_depth', 'has_balance', 'throat_width', 'water_circuit',
            'grip_extension_length', 'eccentricity', 'eccentricity_direction',
            'eccentricity_to_center', 'guidance_method', 'static_arm_eccentricity',
            'static_electrode_arm_end', 'moving_arm_eccentricity', 'moving_electrode_arm_end',
            'pivot_to_drive_center_dist', 'static_arm_front_length', 'static_arm_front_height',
            'moving_arm_front_length', 'moving_arm_front_height', 'pdf_file_path',
            'step_file_path', 'bmp_file_path'
        ]
        
        with transaction.atomic():
            if products_to_create:
                Product.objects.bulk_create(products_to_create, batch_size=batch_size)
            if products_to_update:
                Product.objects.bulk_update(
                    products_to_update,
                    fields=all_fields,
                    batch_size=batch_size
                )

        total_time = time.time() - start_time
        logger.info(f'CSV导入完成：新增 {created_count} 条，更新 {updated_count} 条，耗时 {total_time:.2f} 秒，总记录数 {created_count + updated_count} 条')
        
        messages.success(
            request,
            f'{csv_file.name} 导入成功！新增 {created_count} 条，更新 {updated_count} 条。耗时 {total_time:.2f} 秒。'
        )
        return redirect('clamps:import_csv')

    return render(request, 'management/import_csv.html')

def sync_files_core():
    """文件同步核心逻辑"""
    import logging
    import time
    from django.conf import settings
    import os
    from collections import defaultdict
    from django.db import transaction
    from .models import Product
    
    logger = logging.getLogger(__name__)
    
    start_time = time.time()
    
    media_root = settings.MEDIA_ROOT
    if not os.path.isdir(media_root):
        logger.error(f'媒体目录 {media_root} 不存在。')
        return False, f'媒体目录 {media_root} 不存在。'

    # 1. 优化产品查询：只获取需要的字段值，减少内存占用
    products = Product.objects.all().only(
        'id', 'drawing_no_1',
        'pdf_file_path', 'step_file_path', 'bmp_file_path'
    )
    # 优化：预处理drawing_no_1，构建更高效的映射
    product_map = {}
    for p in products:
        if p.drawing_no_1:
            key = p.drawing_no_1.strip().upper()
            product_map[key] = p

    # 2. 需要批量更新的容器
    to_update = defaultdict(list)
    batch_size = 10000  # 优化：增大批量更新大小

    # 3. 文件后缀 -> 模型字段
    ext_field = {
        '.pdf': 'pdf_file_path',
        '.step': 'step_file_path',
        '.bmp': 'bmp_file_path',
    }

    updated = unmatch = 0
    unmatched_files = []
    all_unmatched_files = []  # 保存所有未匹配文件

    # 4. 遍历 media/ 下所有文件 - 优化：使用scandir替代os.walk
    processed_files = 0
    
    def scan_directory(path):
        nonlocal updated, unmatch, processed_files, unmatched_files, all_unmatched_files
        
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    # 递归处理子目录
                    scan_directory(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    processed_files += 1
                    filename = entry.name
                    name, ext = os.path.splitext(filename.lower())
                    if ext not in ext_field:
                        continue

                    # 优化：一次性替换所有后缀
                    clean = name.upper()
                    if clean.endswith(('_PDF', '_STEP', '_BMP')):
                        clean = clean[:-4]  # 移除最后4个字符
                    
                    product = product_map.get(clean)
                    if not product:
                        unmatch += 1
                        all_unmatched_files.append(filename)  # 保存所有未匹配文件
                        if len(unmatched_files) < 5:  # 只保留前5个未匹配文件用于消息提示
                            unmatched_files.append(filename)
                        continue

                    field = ext_field[ext]
                    # 只保留文件名
                    if getattr(product, field) != filename:
                        setattr(product, field, filename)
                        to_update[field].append(product)
                        updated += 1
    
    scan_directory(media_root)

    # 5. 批量更新 - 优化：使用更大的批量大小
    with transaction.atomic():
        for field, objs in to_update.items():
            # 分批次更新，减少内存占用和数据库压力
            for i in range(0, len(objs), batch_size):
                batch = objs[i:i+batch_size]
                Product.objects.bulk_update(batch, [field])

    # 6. 保存所有未匹配文件到日志文件
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    unmatched_log_path = os.path.join(log_dir, 'unmatched_files.log')
    
    with open(unmatched_log_path, 'w', encoding='utf-8') as f:
        f.write(f'# 文件同步未匹配文件记录 - 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n')
        f.write(f'# 总处理文件数：{processed_files}，未匹配文件数：{unmatch}\n')
        f.write(f'# 媒体目录：{media_root}\n')
        f.write('\n')
        for filename in sorted(all_unmatched_files):
            f.write(f'{filename}\n')
    
    logger.debug(f'未匹配文件列表已保存到：{unmatched_log_path}')

    # 7. 计算耗时并返回结果
    total_time = time.time() - start_time
    msg = f'同步完成：处理 {processed_files} 个文件，更新 {updated} 条记录。耗时 {total_time:.2f} 秒。'
    if unmatch:
        msg += f' 未匹配 {unmatch} 个文件'
        if unmatched_files:
            msg += f'：{', '.join(unmatched_files)}'
            if unmatch > 5:
                msg += ' ...\n未匹配文件完整列表已保存到 logs/unmatched_files.log'
    
    logger.debug(f'{msg}')
    return True, msg


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def sync_files(request):
    if request.method == 'POST':
        # 执行同步操作
        success, msg = sync_files_core()
        
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        
        return redirect('clamps:management_dashboard')
    
    # GET请求，直接返回仪表板，不执行同步操作
    return redirect('clamps:management_dashboard')


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def view_unmatched_files(request):
    """查看未匹配文件列表"""
    import os
    from django.conf import settings
    
    # 读取未匹配文件日志
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    unmatched_log_path = os.path.join(log_dir, 'unmatched_files.log')
    
    unmatched_files = []
    log_info = {
        'generated_time': '未生成',
        'total_processed': 0,
        'total_unmatched': 0,
        'media_root': '',
    }
    
    if os.path.exists(unmatched_log_path):
        with open(unmatched_log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 解析日志头信息
            if line.startswith('# 文件同步未匹配文件记录'):
                log_info['generated_time'] = line.split('生成时间：')[1]
            elif line.startswith('# 总处理文件数'):
                parts = line.split('，')
                log_info['total_processed'] = int(parts[0].split('：')[1])
                log_info['total_unmatched'] = int(parts[1].split('：')[1])
            elif line.startswith('# 媒体目录'):
                log_info['media_root'] = line.split('：')[1]
            elif not line.startswith('#'):
                unmatched_files.append(line)
    
    return render(request, 'management/unmatched_files.html', {
        'unmatched_files': unmatched_files,
        'log_info': log_info,
    })


# 仕样管理相关视图
@login_required
@user_passes_test(is_staff_or_superuser)
def create_style_link(request):
    """创建新仕样链接"""
    if request.method == 'POST':
        # 生成唯一标识符
        while True:
            unique_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
            # 检查是否已存在
            if not StyleLink.objects.filter(unique_id=unique_id).exists():
                break
        
        # 获取表单数据
        customer_name = request.POST.get('customer_name', '').strip()
        project_name = request.POST.get('project_name', '').strip()
        style_number = request.POST.get('style_number', '').strip()
        
        # 将三个字段合并为一个name字符串
        name_parts = []
        if customer_name:
            name_parts.append(customer_name)
        if project_name:
            name_parts.append(project_name)
        if style_number:
            name_parts.append(style_number)
        name = '_'.join(name_parts)
        
        expires_days = request.POST.get('expires_days', '0')
        max_clicks = request.POST.get('max_clicks', '0')
        
        # 处理有效期
        expires_at = None
        if expires_days and int(expires_days) > 0:
            expires_at = timezone.now() + timedelta(days=int(expires_days))
        
        # 处理搜索配置
        # 获取产品分类
        product_categories = request.POST.getlist('product_categories[]')
        
        # 获取变压器类型
        transformers = request.POST.getlist('transformers[]')
        
        # 获取MOTOR厂家类型
        motor_manufacturers = request.POST.getlist('motor_manufacturers[]')
        
        # 获取齿轮箱型式
        gearbox_types = request.POST.getlist('gearbox_types[]')
        
        # 获取启用的其他搜索字段
        enabled_fields = request.POST.getlist('enabled_fields[]')
        
        # 处理固定字段
        fixed_fields = {}
        for key in request.POST:
            if key.startswith('fixed_fields['):
                # 提取字段名
                field_name = key[len('fixed_fields['):-1]
                value = request.POST[key]
                if value:
                    fixed_fields[field_name] = value
        
        search_config = {
            'product_categories': product_categories,
            'transformers': transformers,
            'motor_manufacturers': motor_manufacturers,
            'gearbox_types': gearbox_types,
            'enabled_fields': enabled_fields,
            'fixed_fields': fixed_fields
        }
        
        # 创建仕样链接
        style_link = StyleLink.objects.create(
            unique_id=unique_id,
            name=name,
            ai_disabled=True,  # 全局禁用AI智能搜索
            expires_at=expires_at,
            max_clicks=int(max_clicks),
            search_config=search_config,
            created_by=request.user
        )
        
        messages.success(request, '仕样链接创建成功！')
        return redirect('clamps:my_style_links')
    
    # GET请求，显示创建表单
    return render(request, 'management/create_style_link.html')


@login_required
@user_passes_test(is_staff_or_superuser)
def my_style_links(request):
    """管理我的仕样链接"""
    # 实现权限控制：普通管理员只能查看和管理自己创建的链接，超级管理员可以查看所有链接
    if request.user.is_superuser:
        style_links = StyleLink.objects.all()
    else:
        style_links = StyleLink.objects.filter(created_by=request.user)
    
    # 处理删除请求
    if request.method == 'POST' and 'delete' in request.POST:
        link_id = request.POST.get('link_id')
        style_link = get_object_or_404(StyleLink, id=link_id)
        # 检查权限
        if request.user.is_superuser or style_link.created_by == request.user:
            style_link.delete()
            messages.success(request, '仕样链接已删除！')
        else:
            messages.error(request, '您没有权限删除此链接！')
        return redirect('clamps:my_style_links')
    
    # 处理更新请求
    if request.method == 'POST' and 'update' in request.POST:
        link_id = request.POST.get('link_id')
        style_link = get_object_or_404(StyleLink, id=link_id)
        # 检查权限
        if request.user.is_superuser or style_link.created_by == request.user:
            name = request.POST.get('name', '').strip()
            expires_days = request.POST.get('expires_days', '0')
            max_clicks = request.POST.get('max_clicks', '0')
            is_active = request.POST.get('is_active') == 'on'
            
            # 更新链接信息
            style_link.name = name
            style_link.is_active = is_active
            style_link.max_clicks = int(max_clicks)
            
            # 更新有效期
            if expires_days and int(expires_days) > 0:
                style_link.expires_at = timezone.now() + timedelta(days=int(expires_days))
            else:
                style_link.expires_at = None
            
            style_link.save()
            messages.success(request, '仕样链接已更新！')
        else:
            messages.error(request, '您没有权限更新此链接！')
        return redirect('clamps:my_style_links')
    
    context = {
        'style_links': style_links
    }
    return render(request, 'management/my_style_links.html', context)


@login_required
def style_search(request, unique_id):
    """处理仕样链接的搜索请求"""
    # 获取仕样链接
    try:
        style_link = StyleLink.objects.get(unique_id=unique_id)
        
        # 检查链接是否可用
        if not style_link.can_be_clicked():
            messages.error(request, '该仕样链接已不可用！')
            return redirect('clamps:search')
        
        # 增加点击次数
        style_link.increment_click()
        
        # 设置会话状态，标记当前是从仕样搜索页面进入
        request.session['from_style_search'] = True
        request.session['style_search_unique_id'] = unique_id
        
        # 记录用户访问
        is_valid = style_link.can_be_clicked()
        with transaction.atomic():
            # 检查是否已存在访问记录
            visit, created = UserStyleLinkVisit.objects.get_or_create(
                user=request.user,
                style_link=style_link,
                defaults={
                    'visit_count': 1,
                    'last_visited_at': timezone.now(),
                    'is_valid': is_valid,
                    'link_name': style_link.name,
                    'unique_id': style_link.unique_id
                }
            )
            if not created:
                # 如果记录已存在，更新访问次数和其他信息
                visit.visit_count += 1
                visit.last_visited_at = timezone.now()
                visit.is_valid = is_valid
                visit.link_name = style_link.name
                visit.unique_id = style_link.unique_id
                visit.save()
    except StyleLink.DoesNotExist:
        messages.error(request, '该仕样链接不存在或已失效！')
        return redirect('clamps:search')
    
    # 准备搜索配置上下文
    search_config = style_link.search_config
    
    # 确保所有必要的配置项都存在
    product_categories = search_config.get('product_categories', [])
    transformers = search_config.get('transformers', [])
    motor_manufacturers = search_config.get('motor_manufacturers', [])
    gearbox_types = search_config.get('gearbox_types', [])
    enabled_fields = search_config.get('enabled_fields', [])
    fixed_fields = search_config.get('fixed_fields', {})
    
    # 处理搜索请求
    if request.method == 'GET':
        # 检查是否有实际的搜索参数（排除浏览器自动添加的参数）
        actual_search_params = request.GET.copy()
        # 移除浏览器自动添加的参数
        for param in ['ide_webview_request_time']:
            if param in actual_search_params:
                actual_search_params.pop(param)
        
        if len(actual_search_params) > 0:
            # 构建搜索参数
            query_params = request.GET.copy()
            
            # 应用固定字段
            for field, value in fixed_fields.items():
                if field not in query_params:
                    query_params[field] = value
            
            # 应用产品分类
            if product_categories and 'category' not in query_params:
                # 如果只有一个产品分类，直接使用
                if len(product_categories) == 1:
                    # 处理推荐分类，转换为实际分类名称
                    category = product_categories[0]
                    if category == 'X2C-C_recommended':
                        category = 'X2C-C'
                    elif category == 'X2C-X_recommended':
                        category = 'X2C-X'
                    query_params['category'] = category
            
            # 应用变压器类型
            if transformers and 'transformer' not in query_params:
                # 如果只有一个变压器类型，直接使用
                if len(transformers) == 1:
                    query_params['transformer'] = transformers[0]
            
            # 应用MOTOR厂家类型
            if motor_manufacturers and 'motor_manufacturer' not in query_params:
                # 如果只有一个MOTOR厂家类型，直接使用
                if len(motor_manufacturers) == 1:
                    query_params['motor_manufacturer'] = motor_manufacturers[0]
            
            # 应用齿轮箱型式
            if gearbox_types and 'gearbox_type' not in query_params:
                # 如果只有一个齿轮箱型式，直接使用
                if len(gearbox_types) == 1:
                    query_params['gearbox_type'] = gearbox_types[0]
            
            # 如果有搜索参数，重定向到普通搜索结果页面
            return redirect(f"{reverse('clamps:search_results')}?{query_params.urlencode()}")
    
    context = {
        'style_link': style_link,
        'search_config': search_config,
        'product_categories': product_categories,
        'transformers': transformers,
        'motor_manufacturers': motor_manufacturers,
        'gearbox_types': gearbox_types,
        'enabled_fields': enabled_fields,
        'fixed_fields': fixed_fields,
        'is_style_search': True
    }
    return render(request, 'style_search.html', context)


@login_required
def empty_style_search(request):
    """处理空的仕样搜索路径请求"""
    messages.error(request, '该仕样链接不存在或已失效！')
    return redirect('clamps:search')

@login_required
def empty_style_search_en(request):
    """处理空的仕样搜索英文路径请求"""
    messages.error(request, "Style search link not found!")
    return redirect('clamps:search_en')


def pdf_viewer(request, pdf_filename):
    """PDF阅读器视图 - 统一处理中英文PDF，通过文件名_en后缀区分"""
    # 新的命名规则：中文PDF文件已改为英文文件名，英文PDF使用_en后缀
    # 映射旧中文文件名到新英文文件名
    pdf_mapping = {
        # 旧中文文件名 -> 新英文文件名
        '产品搜索使用指南.pdf': 'Product_Search_User_Guide.pdf',
        '用户协议.pdf': 'User_Agreement.pdf',
        '隐私政策.pdf': 'Privacy_Policy.pdf',
        'csv文件导入前数据标准化流程.pdf': 'CSV_Data_Standardization_Guide.pdf',
        '获取media文件标准化流程.pdf': 'Media_File_Standardization_Guide.pdf',
        # 旧中文文件名 -> 新英文_en文件名（兼容旧链接）
        '产品搜索使用指南_en.pdf': 'Product_Search_User_Guide_en.pdf',
        '用户协议_en.pdf': 'User_Agreement_en.pdf',
        '隐私政策_en.pdf': 'Privacy_Policy_en.pdf'
    }
    
    # 使用映射后的PDF文件名
    mapped_pdf_filename = pdf_mapping.get(pdf_filename, pdf_filename)
    
    # 构建PDF文件的完整URL
    pdf_url = f"/static/pdf/{mapped_pdf_filename}"
    
    # 提取文件名作为标题（去除.pdf扩展名）
    pdf_title = mapped_pdf_filename.replace('.pdf', '')
    
    # 根据文件名_en后缀决定使用哪个模板
    if mapped_pdf_filename.endswith('_en.pdf'):
        # 英文PDF，使用英文模板
        return render(request, 'pdf_viewer_en.html', {
            'pdf_url': pdf_url,
            'pdf_title': pdf_title
        })
    else:
        # 中文PDF，使用中文模板
        return render(request, 'pdf_viewer.html', {
            'pdf_url': pdf_url,
            'pdf_title': pdf_title
        })





def style_search_en(request, unique_id):
    """仕样搜索英文页面"""
    try:
        style_link = StyleLink.objects.get(unique_id=unique_id)
        
        # 更新点击次数
        style_link.click_count += 1
        style_link.save()
        
        # 设置会话标记
        request.session['from_style_search'] = True
        request.session['style_search_unique_id'] = unique_id
        
        # 记录用户访问
        is_valid = style_link.can_be_clicked()
        with transaction.atomic():
            # 检查是否已存在访问记录
            visit, created = UserStyleLinkVisit.objects.get_or_create(
                user=request.user,
                style_link=style_link,
                defaults={
                    'visit_count': 1,
                    'last_visited_at': timezone.now(),
                    'is_valid': is_valid,
                    'link_name': style_link.name,
                    'unique_id': style_link.unique_id
                }
            )
            if not created:
                # 如果记录已存在，更新访问次数和其他信息
                visit.visit_count += 1
                visit.last_visited_at = timezone.now()
                visit.is_valid = is_valid
                visit.link_name = style_link.name
                visit.unique_id = style_link.unique_id
                visit.save()
    except StyleLink.DoesNotExist:
        messages.error(request, "Style search link not found!")
        return redirect('clamps:search_en')
    
    # 准备搜索配置上下文
    search_config = style_link.search_config
    
    # 确保所有必要的配置项都存在
    product_categories = search_config.get('product_categories', [])
    transformers = search_config.get('transformers', [])
    motor_manufacturers = search_config.get('motor_manufacturers', [])
    gearbox_types = search_config.get('gearbox_types', [])
    enabled_fields = search_config.get('enabled_fields', [])
    fixed_fields = search_config.get('fixed_fields', {})
    
    # 处理搜索请求
    if request.method == 'GET':
        # 检查是否有实际的搜索参数（排除浏览器自动添加的参数）
        actual_search_params = request.GET.copy()
        # 移除浏览器自动添加的参数
        for param in ['ide_webview_request_time']:
            if param in actual_search_params:
                actual_search_params.pop(param)
        
        if len(actual_search_params) > 0:
            # 构建搜索参数
            query_params = request.GET.copy()
            
            # 应用固定字段
            for field, value in fixed_fields.items():
                if field not in query_params:
                    query_params[field] = value
            
            # 应用产品分类
            if product_categories and 'category' not in query_params:
                # 如果只有一个产品分类，直接使用
                if len(product_categories) == 1:
                    # 处理推荐分类，转换为实际分类名称
                    category = product_categories[0]
                    if category == 'X2C-C_recommended':
                        category = 'X2C-C'
                    elif category == 'X2C-X_recommended':
                        category = 'X2C-X'
                    query_params['category'] = category
            
            # 应用变压器类型
            if transformers and 'transformer' not in query_params:
                # 如果只有一个变压器类型，直接使用
                if len(transformers) == 1:
                    query_params['transformer'] = transformers[0]
            
            # 应用MOTOR厂家类型
            if motor_manufacturers and 'motor_manufacturer' not in query_params:
                # 如果只有一个MOTOR厂家类型，直接使用
                if len(motor_manufacturers) == 1:
                    query_params['motor_manufacturer'] = motor_manufacturers[0]
            
            # 应用齿轮箱型式
            if gearbox_types and 'gearbox_type' not in query_params:
                # 如果只有一个齿轮箱型式，直接使用
                if len(gearbox_types) == 1:
                    query_params['gearbox_type'] = gearbox_types[0]
            
            # 如果有搜索参数，重定向到普通搜索结果页面
            return redirect(f"{reverse('clamps:search_results_en')}?{query_params.urlencode()}")
    
    context = {
        'style_link': style_link,
        'search_config': search_config,
        'product_categories': product_categories,
        'transformers': transformers,
        'motor_manufacturers': motor_manufacturers,
        'gearbox_types': gearbox_types,
        'enabled_fields': enabled_fields,
        'fixed_fields': fixed_fields,
        'is_style_search': True
    }
    return render(request, 'style_search_en.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def edit_style_link(request, link_id):
    """编辑仕样链接"""
    style_link = get_object_or_404(StyleLink, id=link_id)
    
    # 检查权限
    if not request.user.is_superuser and style_link.created_by != request.user:
        messages.error(request, '您没有权限编辑此链接！')
        return redirect('clamps:my_style_links')
    
    if request.method == 'POST':
        # 获取表单数据
        customer_name = request.POST.get('customer_name', '').strip()
        project_name = request.POST.get('project_name', '').strip()
        style_number = request.POST.get('style_number', '').strip()
        
        # 将三个字段合并为一个name字符串
        name_parts = []
        if customer_name:
            name_parts.append(customer_name)
        if project_name:
            name_parts.append(project_name)
        if style_number:
            name_parts.append(style_number)
        name = '_'.join(name_parts)
        
        expires_days = request.POST.get('expires_days', '0')
        max_clicks = request.POST.get('max_clicks', '0')
        
        # 处理有效期
        expires_at = None
        if expires_days and int(expires_days) > 0:
            expires_at = timezone.now() + timedelta(days=int(expires_days))
        
        # 处理搜索配置
        # 获取产品分类
        product_categories = request.POST.getlist('product_categories[]')
        
        # 获取变压器类型
        transformers = request.POST.getlist('transformers[]')
        
        # 获取MOTOR厂家类型
        motor_manufacturers = request.POST.getlist('motor_manufacturers[]')
        
        # 获取齿轮箱型式
        gearbox_types = request.POST.getlist('gearbox_types[]')
        
        # 获取启用的其他搜索字段
        enabled_fields = request.POST.getlist('enabled_fields[]')
        
        # 处理固定字段
        fixed_fields = {}
        for key in request.POST:
            if key.startswith('fixed_fields['):
                # 提取字段名
                field_name = key[len('fixed_fields['):-1]
                value = request.POST[key]
                if value:
                    fixed_fields[field_name] = value
        
        search_config = {
            'product_categories': product_categories,
            'transformers': transformers,
            'motor_manufacturers': motor_manufacturers,
            'gearbox_types': gearbox_types,
            'enabled_fields': enabled_fields,
            'fixed_fields': fixed_fields
        }
        
        # 更新仕样链接
        style_link.name = name
        style_link.expires_at = expires_at
        style_link.max_clicks = int(max_clicks)
        style_link.search_config = search_config
        style_link.save()
        
        messages.success(request, '仕样链接已更新！')
        return redirect('clamps:my_style_links')
    
    # 计算有效期天数
    if style_link.expires_at:
        # 使用当前时间计算剩余天数，而不是创建时间
        expires_days = max(0, (style_link.expires_at - timezone.now()).days)
    else:
        expires_days = 0
    
    # 将name字段拆分为三个字段
    name_parts = style_link.name.split('_') if style_link.name else []
    customer_name = name_parts[0] if len(name_parts) > 0 else ''
    project_name = name_parts[1] if len(name_parts) > 1 else ''
    style_number = name_parts[2] if len(name_parts) > 2 else ''
    
    context = {
        'style_link': style_link,
        'expires_days': expires_days,
        'customer_name': customer_name,
        'project_name': project_name,
        'style_number': style_number
    }
    return render(request, 'management/edit_style_link.html', context)


import requests
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_http_methods(["GET"])
def gitee_releases_latest(request, owner, repo):
    """
    Gitee API代理视图，解决前端CORS问题
    获取指定仓库的最新发行版信息
    """
    try:
        # Gitee API配置
        gitee_token = 'a09da64c1d9e9c7420a18dfd838890b0'
        gitee_api_base = 'https://gitee.com/api/v5'
        
        # 构建Gitee API URL
        url = f"{gitee_api_base}/repos/{owner}/{repo}/releases/latest"
        
        # 设置请求头，包含访问令牌
        headers = {
            'Authorization': f'token {gitee_token}',
            'User-Agent': 'Django-Gitee-Proxy/1.0'
        }
        
        # 发送请求到Gitee API
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # 只返回需要的字段，减少数据传输
            result = {
                'tag_name': data.get('tag_name'),
                'name': data.get('name'),
                'published_at': data.get('published_at'),
                'html_url': data.get('html_url')
            }
            return JsonResponse(result)
        else:
            return JsonResponse({
                'error': f'Gitee API返回错误: {response.status_code}',
                'message': response.text
            }, status=response.status_code)
            
    except requests.exceptions.Timeout:
        return JsonResponse({
            'error': '请求超时',
            'message': 'Gitee API请求超时，请稍后重试'
        }, status=408)
        
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'error': '网络请求失败',
            'message': str(e)
        }, status=500)
        
    except Exception as e:
        return JsonResponse({
            'error': '服务器内部错误',
            'message': str(e)
        }, status=500)




# 导入下载数据分析相关函数
import re
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import Log, UserProfile

def api_login_required(view_func):
    """
    自定义API登录装饰器，返回JSON错误而不是HTML重定向
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': '未登录', 'message': '请先登录'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def api_staff_required(view_func):
    """
    自定义API权限装饰器，返回JSON错误而不是HTML重定向
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            return JsonResponse({'error': '权限不足', 'message': '需要管理员权限'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@api_login_required
@api_staff_required
def download_analytics_api(request):
    """
    提供下载数据分析的API接口
    已修改：删除匿名用户统计，不允许有空用户名
    """
    # 获取参数
    days = int(request.GET.get('days', 7))  # 默认7天
    user_filter = request.GET.get('user', 'all')  # 默认全部用户
    
    # 计算时间范围
    end_date = timezone.now()
    # 转换为本地时间
    end_date_local = timezone.localtime(end_date)
    # 如果是今天，从本地时间00:00:00开始统计，否则按天数计算
    if days == 1:
        start_date = timezone.make_aware(datetime.combine(end_date_local.date(), datetime.min.time()))
    else:
        start_date = end_date - timedelta(days=days)
    
    # 基础查询：下载相关的日志
    # 只查询有用户关联的日志（排除匿名用户）
    base_query = Log.objects.filter(
        action_type__in=['download', 'batch_download', 'single_download'],
        timestamp__gte=start_date,
        timestamp__lte=end_date,
        user__isnull=False  # 排除匿名用户
    ).select_related('user')  # 预加载user，减少数据库查询
    
    # 用户筛选
    if user_filter != 'all':
        base_query = base_query.filter(user__username=user_filter)
    
    # 获取所有下载日志
    download_logs = base_query.order_by('timestamp')
    
    # 解析下载数据
    user_stats = defaultdict(lambda: {
        'count': 0,
        'files': 0,
        'size': 0.0,
        'lastDownload': ''
    })
    
    # 初始化日期统计字典
    daily_stats = defaultdict(lambda: {
        'downloads': 0,
        'size': 0.0
    })
    
    for log in download_logs:
        username = log.user.username.strip()
        
        # 过滤掉空用户名
        if not username:
            continue
        
        log_date = log.timestamp.date().isoformat()
        
        # 解析details字段获取文件信息
        size_mb = parse_download_size(log.details)
        file_count = parse_file_count(log.details)
        
        # 更新用户统计
        user_stats[username]['count'] += 1
        user_stats[username]['files'] += file_count
        user_stats[username]['size'] += size_mb
        
        # 更新最后下载时间
        log_time_str = timezone.localtime(log.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        if not user_stats[username]['lastDownload'] or log_time_str > user_stats[username]['lastDownload']:
            user_stats[username]['lastDownload'] = log_time_str
        
        # 更新日期统计
        daily_stats[log_date]['downloads'] += 1
        daily_stats[log_date]['size'] += size_mb
    
    # 生成趋势数据
    trend_data = []
    current_date = start_date.date()
    while current_date <= end_date.date():
        date_str = current_date.isoformat()
        trend_data.append({
            'date': date_str,
            'downloads': daily_stats[date_str]['downloads'],
            'size': round(daily_stats[date_str]['size'], 1)
        })
        current_date += timedelta(days=1)
    
    # 获取活跃用户列表
    active_users = list(user_stats.keys())
    
    # 计算总计数据
    total_downloads = sum(stats['count'] for stats in user_stats.values())
    total_files = sum(stats['files'] for stats in user_stats.values())
    total_size = sum(stats['size'] for stats in user_stats.values())
    active_user_count = len(active_users)
    
    return JsonResponse({
        'users': active_users,
        'downloads': dict(user_stats),
        'trend': trend_data,
        'summary': {
            'totalDownloads': total_downloads,
            'totalFiles': total_files,
            'totalSize': round(total_size, 1),
            'activeUsers': active_user_count
        }
    }, json_dumps_params={'ensure_ascii': False})


def parse_download_size(details):
    """从日志详情中解析下载大小（MB）"""
    try:
        # 匹配单个下载的格式: "File Size: 0.03 MB"
        size_match = re.search(r'File Size: ([\d.]+) MB', details)
        if size_match:
            return float(size_match.group(1))
        # 匹配批量下载的格式: "Total Size: 24.54 MB"
        total_size_match = re.search(r'Total Size: ([\d.]+) MB', details)
        if total_size_match:
            return float(total_size_match.group(1))
    except Exception:
        # 静默处理异常，提高性能
        pass
    return 0.0



def parse_file_count(details):
    """从日志详情中解析下载文件数量"""
    try:
        # 单个文件下载 - 检查Product ID: 或 Drawing No.: 或旧格式
        if ('File Type:' in details and 'Product IDs:' not in details and 'Drawing Nos:' not in details) or 'Product ID:' in details or 'Drawing No.:' in details:
            return 1
        # 批量下载 - 检查Product IDs: 或 Drawing Nos:
        elif 'Product IDs:' in details:
            ids_match = re.search(r'Product IDs: ([\d,]+)', details)
            if ids_match:
                product_ids = [id.strip() for id in ids_match.group(1).split(',') if id.strip().isdigit()]
                # 检查是否下载多种文件类型（both = pdf + step）
                if 'File Type: both' in details:
                    return len(product_ids) * 2
                # 只下载一种文件类型
                else:
                    return len(product_ids)
        elif 'Drawing Nos:' in details:
            # Drawing Nos: 格式下使用逗号分隔的图号，不是数字ID，所以直接计算数量
            nos_match = re.search(r'Drawing Nos: ([^,]+)', details)
            if nos_match:
                drawing_nos = [no.strip() for no in nos_match.group(1).split(',') if no.strip()]
                # 检查是否下载多种文件类型（both = pdf + step）
                if 'File Type: both' in details:
                    return len(drawing_nos) * 2
                # 只下载一种文件类型
                else:
                    return len(drawing_nos)
    except Exception:
        # 静默处理异常，提高性能
        pass
    return 0



@csrf_exempt
def ai_search_api(request):
    """AI智能搜索API接口"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': '仅支持POST请求'
        })
    
    try:
        import json
        from .coze_service import query_coze
        
        # 解析请求数据
        data = json.loads(request.body)
        query_text = data.get('query', '').strip()
        
        if not query_text:
            return JsonResponse({
                'success': False,
                'error': '查询内容不能为空'
            })
        
        # 调用Coze API
        result = query_coze(query_text)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '请求数据格式错误'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        })

@login_required
@user_passes_test(is_staff_or_superuser)
def analytics_view(request):
    """数据分析视图"""
    return render(request, 'management/analytics.html')

@login_required
def get_user_profile_data(request):
    """获取用户配置数据API"""
    try:
        # 每次请求都重新从数据库获取最新数据，避免使用缓存
        user_profile = UserProfile.objects.get(user=request.user)
        
        # 获取密码过期日期
        password_expiry_date = user_profile.get_password_expiry_date()
        if isinstance(password_expiry_date, str):
            expiry_text = password_expiry_date
        else:
            # 转换为本地时间（北京时间）并格式化
            expiry_text = timezone.localtime(password_expiry_date).strftime('%Y-%m-%d %H:%M:%S')
        
        # 确保使用最新的下载统计数据
        # 检查是否需要重置每日统计
        today = timezone.localtime(timezone.now()).date()
        if user_profile.last_download_date != today:
            user_profile.reset_daily_download_stats()
            # 重新获取更新后的数据
            user_profile.refresh_from_db()
        
        return JsonResponse({
            'created_by': user_profile.created_by.username if user_profile.created_by else "N/A",
            'password_expiry_date': expiry_text,
            'max_daily_download_gb': user_profile.max_daily_download_gb,
            'max_daily_download_count': user_profile.max_daily_download_count,
            'daily_download_count': user_profile.daily_download_count,
            'daily_download_size_mb': user_profile.daily_download_size_mb
        })
    except UserProfile.DoesNotExist:
        # 创建新的用户配置
        user_profile = UserProfile.objects.create(user=request.user)
        return JsonResponse({
            'created_by': "N/A",
            'password_expiry_date': "永久有效",
            'max_daily_download_gb': user_profile.max_daily_download_gb,
            'max_daily_download_count': user_profile.max_daily_download_count,
            'daily_download_count': 0,
            'daily_download_size_mb': 0
        })
    except Exception as e:
        print(f"获取用户配置数据失败: {str(e)}")  # 添加错误日志
        return JsonResponse({
            'created_by': "获取失败",
            'password_expiry_date': "获取失败",
            'max_daily_download_gb': "N/A",
            'max_daily_download_count': "N/A",
            'daily_download_count': "N/A",
            'daily_download_size_mb': "N/A"
        })


# 用户反馈相关视图函数
@login_required
def user_feedback(request):
    """用户反馈收集页面（中文）"""
    if request.method == 'POST':
        category = request.POST.get('category')
        related_link = request.POST.get('related_link')
        content = request.POST.get('content')
        contact_name = request.POST.get('contact_name')
        contact_phone = request.POST.get('contact_phone')
        contact_email = request.POST.get('contact_email')
        
        # 验证必填字段
        if not category:
            messages.error(request, '请选择反馈分类')
            return render(request, 'user_feedback.html', {'is_style_search': request.session.get('from_style_search', False)})
        if not content:
            messages.error(request, '请填写内容说明')
            return render(request, 'user_feedback.html', {'is_style_search': request.session.get('from_style_search', False)})
        
        # 创建反馈记录
        feedback = UserFeedback(
            category=category,
            related_link=related_link if related_link else None,
            content=content,
            contact_name=contact_name if contact_name else None,
            contact_phone=contact_phone if contact_phone else None,
            contact_email=contact_email if contact_email else None,
            user=request.user if request.user.is_authenticated else None
        )
        feedback.save()
        
        messages.success(request, '您的反馈已提交成功，感谢您的支持！')
        return redirect('clamps:user_feedback')
    
    return render(request, 'user_feedback.html', {'is_style_search': request.session.get('from_style_search', False)})


@login_required
def user_feedback_en(request):
    """用户反馈收集页面（英文）"""
    is_style_search = request.session.get('from_style_search', False)
    
    if request.method == 'POST':
        category = request.POST.get('category')
        related_link = request.POST.get('related_link')
        content = request.POST.get('content')
        contact_name = request.POST.get('contact_name')
        contact_phone = request.POST.get('contact_phone')
        contact_email = request.POST.get('contact_email')
        
        # 验证必填字段
        if not category:
            messages.error(request, 'Please select feedback category')
            return render(request, 'user_feedback_en.html', {'is_style_search': is_style_search})
        if not content:
            messages.error(request, 'Please fill in content description')
            return render(request, 'user_feedback_en.html', {'is_style_search': is_style_search})
        
        # 创建反馈记录
        feedback = UserFeedback(
            category=category,
            related_link=related_link if related_link else None,
            content=content,
            contact_name=contact_name if contact_name else None,
            contact_phone=contact_phone if contact_phone else None,
            contact_email=contact_email if contact_email else None,
            user=request.user if request.user.is_authenticated else None
        )
        feedback.save()
        
        messages.success(request, 'Your feedback has been submitted successfully, thank you for your support!')
        return redirect('clamps:user_feedback_en')
    
    return render(request, 'user_feedback_en.html', {'is_style_search': is_style_search})


@login_required
def profile(request):
    """个人中心页面"""
    # 获取用户的下载记录，最近100条
    download_logs = Log.objects.filter(
        user=request.user,
        action_type__in=['download', 'batch_download', 'single_download']
    ).order_by('-timestamp')[:100]
    
    # 获取用户访问过的仕样链接记录
    style_link_visits = UserStyleLinkVisit.objects.filter(
        user=request.user
    ).order_by('-last_visited_at')
    
    # 预处理下载日志数据，先收集所有需要查询的产品ID
    temp_logs = []
    product_ids_to_query = []
    
    for log in download_logs:
        log_data = {
            'timestamp': log.timestamp,
            'action_type': log.action_type,
            'details': log.details
        }
        
        # 解析日志详情
        if 'Product IDs:' in log.details:
            log_data['product_id'] = '多个产品'
            log_data['file_type'] = '多个文件'
            # 解析批量下载的文件大小
            if 'Total Size:' in log.details:
                details = log.details
                total_size_part = [part for part in details.split(',') if 'Total Size:' in part][0]
                total_size = total_size_part.split(':')[1].strip()
            else:
                total_size = '未知'
            log_data['file_size'] = total_size
        elif 'Drawing Nos:' in log.details:
            # 解析批量下载的图号
            details = log.details
            
            # 处理多行和逗号分隔的图号
            if 'Drawing Nos:' in details:
                # 找到Drawing Nos:开始的部分
                drawing_nos_start = details.index('Drawing Nos:')
                
                # 查找结束位置 - 排除逗号，因为逗号可能在图号之间
                # 查找可能的结束标记：File Type:、Total Size: 或 Async Task ID:
                end_markers = ['File Type:', 'Total Size:', 'Async Task ID:']
                end_positions = []
                
                for marker in end_markers:
                    pos = details.find(marker, drawing_nos_start)
                    if pos != -1:
                        end_positions.append(pos)
                
                if end_positions:
                    # 使用最接近的结束标记
                    end_pos = min(end_positions)
                    drawing_nos_part = details[drawing_nos_start:end_pos]
                else:
                    # 如果没有找到结束标记，取整个剩余部分
                    drawing_nos_part = details[drawing_nos_start:]
                
                # 提取图号部分并清理
                drawing_nos_content = drawing_nos_part.split(':', 1)[1].strip()
                # 先将逗号替换为空格，再将任意空白字符序列替换为单个逗号+空格，避免双重逗号
                drawing_nos_content = drawing_nos_content.replace(',', ' ')
                drawing_nos = re.sub(r'\s+', ', ', drawing_nos_content).strip()
                # 移除结尾可能存在的逗号
                if drawing_nos.endswith(','):
                    drawing_nos = drawing_nos[:-1]
                drawing_nos = drawing_nos.strip()
                log_data['product_id'] = drawing_nos
            
            # 解析文件类型
            if 'File Type:' in details:
                file_type_part = [part for part in details.split(',') if 'File Type:' in part][0]
                file_type = file_type_part.split(':')[1].strip().upper()
                log_data['file_type'] = file_type
            else:
                log_data['file_type'] = '未知'
            
            # 解析批量下载的文件大小
            if 'Total Size:' in log.details:
                total_size_part = [part for part in details.split(',') if 'Total Size:' in part][0]
                total_size = total_size_part.split(':')[1].strip()
            else:
                total_size = '未知'
            log_data['file_size'] = total_size
        elif 'File Type:' in log.details:
            # 解析单个下载记录
            details = log.details
            
            # 提取产品ID或图号
            if 'Product ID:' in details:
                product_id_part = details.split(',')[0]
                product_id = product_id_part.split(':')[1].strip()
                if product_id != '未知':
                    product_ids_to_query.append(product_id)
            elif 'Drawing No.:' in details:
                # 图号格式已直接包含在日志中，不需要查询
                drawing_no_part = details.split(',')[0]
                drawing_no = drawing_no_part.split(':')[1].strip()
                product_id = drawing_no  # 直接使用图号作为product_id
            else:
                product_id = '未知'
            log_data['product_id'] = product_id
            
            # 提取文件类型
            if 'File Type:' in details:
                file_type_part = [part for part in details.split(',') if 'File Type:' in part][0]
                file_type = file_type_part.split(':')[1].strip().upper()
            else:
                file_type = '未知'
            log_data['file_type'] = file_type
            
            # 提取文件大小，支持Total Size: 格式
            if 'Total Size:' in details:
                file_size_part = [part for part in details.split(',') if 'Total Size:' in part][0]
                file_size = file_size_part.split(':')[1].strip()
            else:
                file_size = '未知'
            log_data['file_size'] = file_size
        else:
            log_data['product_id'] = '未知'
            log_data['file_type'] = '未知'
            log_data['file_size'] = '未知'
        
        temp_logs.append(log_data)
    
    # 批量查询产品图号
    product_id_to_drawing_no = {}
    if product_ids_to_query:
        # 转换为整数列表，排除非数字ID
        valid_product_ids = []
        for pid in product_ids_to_query:
            if pid.isdigit():
                valid_product_ids.append(int(pid))
        
        # 查询所有产品
        products = Product.objects.filter(id__in=valid_product_ids)
        # 创建产品ID到图号的映射
        for product in products:
            product_id_to_drawing_no[str(product.id)] = product.drawing_no_1 or str(product.id)
    
    # 替换产品ID为图号
    processed_download_logs = []
    for log_data in temp_logs:
        pid = log_data['product_id']
        if pid.isdigit() and pid in product_id_to_drawing_no:
            log_data['product_id'] = product_id_to_drawing_no[pid]
        processed_download_logs.append(log_data)
    
    # 获取用户的反馈记录，最近100条
    user_feedbacks = UserFeedback.objects.filter(
        user=request.user
    ).order_by('-created_at')[:100]
    
    # 分页处理下载记录，默认每页10条
    download_paginator = Paginator(processed_download_logs, 10)
    download_page_number = request.GET.get('download_page')
    download_page_obj = download_paginator.get_page(download_page_number)
    
    # 分页处理反馈记录，默认每页10条
    feedback_paginator = Paginator(user_feedbacks, 10)
    feedback_page_number = request.GET.get('feedback_page')
    feedback_page_obj = feedback_paginator.get_page(feedback_page_number)
    
    # 分页处理仕样链接访问记录，默认每页10条
    style_link_paginator = Paginator(style_link_visits, 10)
    style_link_page_number = request.GET.get('style_link_page')
    style_link_page_obj = style_link_paginator.get_page(style_link_page_number)
    
    context = {
        'download_logs': download_page_obj,
        'user_feedbacks': feedback_page_obj,
        'style_link_visits': style_link_page_obj,
        'is_style_search': request.session.get('from_style_search', False)
    }
    return render(request, 'profile.html', context)


@login_required
def profile_en(request):
    """个人中心页面（英文）"""
    # 获取用户的下载记录，最近100条
    download_logs = Log.objects.filter(
        user=request.user,
        action_type__in=['download', 'batch_download', 'single_download']
    ).order_by('-timestamp')[:100]
    
    # 获取用户访问过的仕样链接记录
    style_link_visits = UserStyleLinkVisit.objects.filter(
        user=request.user
    ).order_by('-last_visited_at')
    
    # 预处理下载日志数据，先收集所有需要查询的产品ID
    temp_logs = []
    product_ids_to_query = []
    
    for log in download_logs:
        log_data = {
            'timestamp': log.timestamp,
            'action_type': log.action_type,
            'details': log.details
        }
        
        # 解析日志详情
        if 'Product IDs:' in log.details:
            log_data['product_id'] = 'Multiple Products'
            log_data['file_type'] = 'Multiple Files'
            # 解析批量下载的文件大小
            if 'Total Size:' in log.details:
                details = log.details
                total_size_part = [part for part in details.split(',') if 'Total Size:' in part][0]
                total_size = total_size_part.split(':')[1].strip()
            else:
                total_size = 'Unknown'
            log_data['file_size'] = total_size
        elif 'Drawing Nos:' in log.details:
            # 解析批量下载的图号
            details = log.details
            
            # 处理多行和逗号分隔的图号
            if 'Drawing Nos:' in details:
                # 找到Drawing Nos:开始的部分
                drawing_nos_start = details.index('Drawing Nos:')
                
                # 查找结束位置 - 排除逗号，因为逗号可能在图号之间
                # 查找可能的结束标记：File Type:、Total Size: 或 Async Task ID:
                end_markers = ['File Type:', 'Total Size:', 'Async Task ID:']
                end_positions = []
                
                for marker in end_markers:
                    pos = details.find(marker, drawing_nos_start)
                    if pos != -1:
                        end_positions.append(pos)
                
                if end_positions:
                    # 使用最接近的结束标记
                    end_pos = min(end_positions)
                    drawing_nos_part = details[drawing_nos_start:end_pos]
                else:
                    # 如果没有找到结束标记，取整个剩余部分
                    drawing_nos_part = details[drawing_nos_start:]
                
                # 提取图号部分并清理
                drawing_nos_content = drawing_nos_part.split(':', 1)[1].strip()
                # 先将逗号替换为空格，再将任意空白字符序列替换为单个逗号+空格，避免双重逗号
                drawing_nos_content = drawing_nos_content.replace(',', ' ')
                drawing_nos = re.sub(r'\s+', ', ', drawing_nos_content).strip()
                # 移除结尾可能存在的逗号
                if drawing_nos.endswith(','):
                    drawing_nos = drawing_nos[:-1]
                drawing_nos = drawing_nos.strip()
                log_data['product_id'] = drawing_nos
            
            # 解析文件类型
            if 'File Type:' in details:
                file_type_part = [part for part in details.split(',') if 'File Type:' in part][0]
                file_type = file_type_part.split(':')[1].strip().upper()
                log_data['file_type'] = file_type
            else:
                log_data['file_type'] = 'Unknown'
            
            # 解析批量下载的文件大小
            if 'Total Size:' in log.details:
                total_size_part = [part for part in details.split(',') if 'Total Size:' in part][0]
                total_size = total_size_part.split(':')[1].strip()
            else:
                total_size = 'Unknown'
            log_data['file_size'] = total_size
        elif 'File Type:' in log.details:
            # 解析单个下载记录
            details = log.details
            
            # 提取产品ID或图号
            if 'Product ID:' in details:
                product_id_part = details.split(',')[0]
                product_id = product_id_part.split(':')[1].strip()
                if product_id != 'Unknown':
                    product_ids_to_query.append(product_id)
            elif 'Drawing No.:' in details:
                # 图号格式已直接包含在日志中，不需要查询
                drawing_no_part = details.split(',')[0]
                drawing_no = drawing_no_part.split(':')[1].strip()
                product_id = drawing_no  # 直接使用图号作为product_id
            else:
                product_id = 'Unknown'
            log_data['product_id'] = product_id
            
            # 提取文件类型
            if 'File Type:' in details:
                file_type_part = [part for part in details.split(',') if 'File Type:' in part][0]
                file_type = file_type_part.split(':')[1].strip().upper()
            else:
                file_type = 'Unknown'
            log_data['file_type'] = file_type
            
            # 提取文件大小，支持Total Size: 格式
            if 'Total Size:' in details:
                file_size_part = [part for part in details.split(',') if 'Total Size:' in part][0]
                file_size = file_size_part.split(':')[1].strip()
            else:
                file_size = 'Unknown'
            log_data['file_size'] = file_size
        else:
            log_data['product_id'] = 'Unknown'
            log_data['file_type'] = 'Unknown'
            log_data['file_size'] = 'Unknown'
        
        temp_logs.append(log_data)
    
    # 批量查询产品图号
    product_id_to_drawing_no = {}
    if product_ids_to_query:
        # 转换为整数列表，排除非数字ID
        valid_product_ids = []
        for pid in product_ids_to_query:
            if pid.isdigit():
                valid_product_ids.append(int(pid))
        
        # 查询所有产品
        products = Product.objects.filter(id__in=valid_product_ids)
        # 创建产品ID到图号的映射
        for product in products:
            product_id_to_drawing_no[str(product.id)] = product.drawing_no_1 or str(product.id)
    
    # 替换产品ID为图号
    processed_download_logs = []
    for log_data in temp_logs:
        pid = log_data['product_id']
        if pid.isdigit() and pid in product_id_to_drawing_no:
            log_data['product_id'] = product_id_to_drawing_no[pid]
        processed_download_logs.append(log_data)
    
    # 获取用户的反馈记录，最近100条
    user_feedbacks = UserFeedback.objects.filter(
        user=request.user
    ).order_by('-created_at')[:100]
    
    # 分页处理下载记录，默认每页10条
    download_paginator = Paginator(processed_download_logs, 10)
    download_page_number = request.GET.get('download_page')
    download_page_obj = download_paginator.get_page(download_page_number)
    
    # 分页处理反馈记录，默认每页10条
    feedback_paginator = Paginator(user_feedbacks, 10)
    feedback_page_number = request.GET.get('feedback_page')
    feedback_page_obj = feedback_paginator.get_page(feedback_page_number)
    
    # 分页处理仕样链接访问记录，默认每页10条
    style_link_paginator = Paginator(style_link_visits, 10)
    style_link_page_number = request.GET.get('style_link_page')
    style_link_page_obj = style_link_paginator.get_page(style_link_page_number)
    
    context = {
        'download_logs': download_page_obj,
        'user_feedbacks': feedback_page_obj,
        'style_link_visits': style_link_page_obj,
        'is_style_search': request.session.get('from_style_search', False)
    }
    return render(request, 'profile_en.html', context)


@login_required
@user_passes_test(is_superuser)
def manage_user_feedback(request):
    """管理用户反馈页面（仅超级管理员可见）"""
    feedback_list = UserFeedback.objects.all().order_by('-created_at')
    
    # 状态选项用于筛选
    status_choices = UserFeedback._meta.get_field('status').choices
    
    # 筛选功能
    status_filter = request.GET.get('status')
    if status_filter:
        feedback_list = feedback_list.filter(status=status_filter)
    
    # 分页
    paginator = Paginator(feedback_list, 10)  # 每页10条
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_choices': status_choices,
        'current_status': status_filter
    }
    
    return render(request, 'management/user_feedback.html', context)


@login_required
@user_passes_test(is_superuser)
def update_feedback_status(request, feedback_id):
    """更新反馈状态（仅超级管理员可见）"""
    feedback = get_object_or_404(UserFeedback, id=feedback_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            # 检查状态是否从非处理状态变为处理状态
            feedback.status = new_status
            
            # 如果状态变为已处理、无法确认或无效反馈，标记为未通知用户
            if feedback.status in ['已处理', '无法确认', '无效反馈']:
                feedback.is_notified = False
            feedback.save()
            
            messages.success(request, '反馈状态已更新')
        return redirect('clamps:manage_user_feedback')


@login_required
@user_passes_test(is_superuser)
def export_user_feedback(request):
    """导出用户反馈为CSV文件（仅超级管理员可见）"""
    import csv
    from django.http import HttpResponse
    
    # 获取筛选条件
    status_filter = request.GET.get('status')
    feedback_list = UserFeedback.objects.all().order_by('-created_at')
    
    if status_filter:
        feedback_list = feedback_list.filter(status=status_filter)
    
    # 记录导出日志
    Log.objects.create(
        user=request.user,
        action_type='export_data',
        details=f'导出用户反馈数据（状态筛选: {status_filter if status_filter else "全部"}）',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # 创建CSV响应
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="user_feedback.csv"'
    
    writer = csv.writer(response)
    # 写入CSV头部
    writer.writerow(['ID', '反馈分类', '反馈内容', '相关链接', '联系方式', '提交用户', '提交时间', '状态'])
    
    # 写入数据
    for feedback in feedback_list:
        contact_info = []
        if feedback.contact_name:
            contact_info.append(f"姓名: {feedback.contact_name}")
        if feedback.contact_phone:
            contact_info.append(f"电话: {feedback.contact_phone}")
        if feedback.contact_email:
            contact_info.append(f"邮箱: {feedback.contact_email}")
        
        contact_str = "，".join(contact_info) if contact_info else "无联系方式"
        username = feedback.user.username if feedback.user else "匿名用户"
        
        writer.writerow([
            feedback.id,
            feedback.category,
            feedback.content,
            feedback.related_link or "无",
            contact_str,
            username,
            feedback.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            feedback.status
        ])
    
    return response
