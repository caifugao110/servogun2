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



import zipfile
import io
import os
from collections import defaultdict
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import Product
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib import messages
import secrets
import string
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import csv
import chardet
import tempfile
import re
import glob

from .models import Category, Product, Log, UserProfile

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
            # 检查密码是否过期
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            if user_profile.is_password_expired():
                logout(request)
                return render(request, 'login.html', {'error': '您的密码已过期，请联系管理员重置。'})

            # 记录登录日志
            log_entry = Log(user=user, action_type='login', ip_address=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', ''))
            log_entry.save()
            return redirect('clamps:home')
        else:
            return render(request, 'login.html', {'error': '无效的用户名或密码'})
    return render(request, 'login.html')

def user_login_en(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            if user_profile.is_password_expired():
                logout(request)
                return render(request, 'login_en.html', {'error': 'Your password has expired, please contact the administrator to reset it.'})
            log_entry = Log(user=user, action_type='login', ip_address=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', ''))
            log_entry.save()
            return redirect('clamps:home_en')
        else:
            return render(request, 'login_en.html', {'error': 'Invalid username or password'})
    return render(request, 'login_en.html')


def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for i in range(length))
    return password

@login_required
def user_logout(request):
    # 记录登出日志
    log_entry = Log(user=request.user, action_type='logout', ip_address=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', ''))
    log_entry.save()
    logout(request)
    messages.info(request, '您已成功登出。') # 添加中文提示信息
    return redirect('clamps:login') # 重定向到中文登录页面

# 新增：专门负责英文登出的视图
@login_required
def user_logout_en(request):
    # 记录登出日志 (可以添加标记以区分)
    log_entry = Log(user=request.user, action_type='logout_en', ip_address=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', ''))
    log_entry.save()
    logout(request)
    messages.info(request, 'You have been successfully logged out.') # 添加英文提示信息
    return redirect('clamps:login_en') # 重定向到英文登录页面


@login_required
def search(request):
    categories = Category.objects.all()
    return render(request, 'search.html', {'categories': categories})

@login_required
def search_en(request):
    categories = Category.objects.all()
    return render(request, 'search_en.html', {'categories': categories})


@login_required
def search_results(request):
    query_params = request.GET.copy()
    category_id = query_params.get('category')
    description = query_params.get('description')
    drawing_no_1 = query_params.get('drawing_no_1')
    sub_category_type = query_params.get('sub_category_type')

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

    queryset = Product.objects.all()

    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if description:
        queryset = queryset.filter(description__icontains=description)
    if drawing_no_1:
        queryset = queryset.filter(drawing_no_1__icontains=drawing_no_1)
    if sub_category_type:
        queryset = queryset.filter(sub_category_type__icontains=sub_category_type)

    # 处理数值范围查询
    def parse_range_query(field_name, query_string, current_queryset):
        if query_string:
            query_string = query_string.strip()
            if '~' in query_string:
                parts = query_string.split('~')
                min_val_str = parts[0].strip()
                max_val_str = parts[1].strip()

                q_objects = Q()
                if min_val_str:
                    try:
                        min_val = float(min_val_str)
                        q_objects &= Q(**{f'{field_name}__gte': min_val})
                    except ValueError:
                        pass # 忽略无效的最小值
                if max_val_str:
                    try:
                        max_val = float(max_val_str)
                        q_objects &= Q(**{f'{field_name}__lte': max_val})
                    except ValueError:
                        pass # 忽略无效的最大值
                
                if q_objects: # 确保有有效的查询条件才应用
                    current_queryset = current_queryset.filter(q_objects)
            else:
                # 精确匹配
                try:
                    exact_val = float(query_string)
                    current_queryset = current_queryset.filter(**{field_name: exact_val})
                except ValueError:
                    pass # 忽略无效的精确值
        return current_queryset

    queryset = parse_range_query('stroke', stroke, queryset)
    queryset = parse_range_query('clamping_force', clamping_force, queryset)
    queryset = parse_range_query('weight', weight, queryset)
    queryset = parse_range_query('throat_depth', throat_depth, queryset)
    queryset = parse_range_query('throat_width', throat_width, queryset)

    if transformer:
        queryset = queryset.filter(transformer__icontains=transformer)
    if electrode_arm_end:
        queryset = queryset.filter(electrode_arm_end__icontains=electrode_arm_end)
    if motor_manufacturer:
        queryset = queryset.filter(motor_manufacturer__icontains=motor_manufacturer)
    if has_balance:
        # 处理中英文版本的has_balance值
        if has_balance in ['有', 'Yes']:
            queryset = queryset.filter(has_balance=True)
        elif has_balance in ['无', 'No']:
            queryset = queryset.filter(has_balance=False)
    
    # 处理动态字段
    dynamic_fields = {}
    for key, value in query_params.items():
        if key not in ["category", "description", "drawing_no_1", "sub_category_type",
                       "stroke", "clamping_force", "weight", "throat_depth", "throat_width",
                       "transformer", "electrode_arm_end", "motor_manufacturer", "has_balance",
                       "transformer_placement", "flange_pcd", "bracket_direction", "water_circuit",
                       "page", "csrfmiddlewaretoken"] and value:
            dynamic_fields[key] = value

    for field_name, field_value in dynamic_fields.items():
        # 假设动态字段都是文本类型，进行模糊查询
        queryset = queryset.filter(**{f'{field_name}__icontains': field_value})

    # 记录搜索日志
    log_entry = Log(user=request.user, action_type='search', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=str(query_params))
    log_entry.save()

    paginator = Paginator(queryset, 20)  # 每页20条记录
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_results': paginator.count,
        'query_params': query_params,
    }
    return render(request, 'search_results.html', context)

@login_required
def search_results_en(request):
    query_params = request.GET.copy()
    category_id = query_params.get('category')
    description = query_params.get('description')
    drawing_no_1 = query_params.get('drawing_no_1')
    sub_category_type = query_params.get('sub_category_type')

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

    queryset = Product.objects.all()

    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if description:
        queryset = queryset.filter(description__icontains=description)
    if drawing_no_1:
        queryset = queryset.filter(drawing_no_1__icontains=drawing_no_1)
    if sub_category_type:
        queryset = queryset.filter(sub_category_type__icontains=sub_category_type)

    def parse_range_query(field_name, query_string, current_queryset):
        if query_string:
            query_string = query_string.strip()
            if '~' in query_string:
                parts = query_string.split('~')
                min_val_str = parts[0].strip()
                max_val_str = parts[1].strip()

                q_objects = Q()
                if min_val_str:
                    try:
                        min_val = float(min_val_str)
                        q_objects &= Q(**{f'{field_name}__gte': min_val})
                    except ValueError:
                        pass
                if max_val_str:
                    try:
                        max_val = float(max_val_str)
                        q_objects &= Q(**{f'{field_name}__lte': max_val})
                    except ValueError:
                        pass
                
                if q_objects:
                    current_queryset = current_queryset.filter(q_objects)
            else:
                try:
                    exact_val = float(query_string)
                    current_queryset = current_queryset.filter(**{field_name: exact_val})
                except ValueError:
                    pass
        return current_queryset

    queryset = parse_range_query('stroke', stroke, queryset)
    queryset = parse_range_query('clamping_force', clamping_force, queryset)
    queryset = parse_range_query('weight', weight, queryset)
    queryset = parse_range_query('throat_depth', throat_depth, queryset)
    queryset = parse_range_query('throat_width', throat_width, queryset)

    if transformer:
        queryset = queryset.filter(transformer__icontains=transformer)
    if electrode_arm_end:
        queryset = queryset.filter(electrode_arm_end__icontains=electrode_arm_end)
    if motor_manufacturer:
        queryset = queryset.filter(motor_manufacturer__icontains=motor_manufacturer)
    if has_balance:
        # 处理中英文版本的has_balance值
        if has_balance in ['有', 'Yes']:
            queryset = queryset.filter(has_balance=True)
        elif has_balance in ['无', 'No']:
            queryset = queryset.filter(has_balance=False)
    
    # 处理动态字段
    dynamic_fields = {}
    for key, value in query_params.items():
        if key not in ["category", "description", "drawing_no_1", "sub_category_type",
                       "stroke", "clamping_force", "weight", "throat_depth", "throat_width",
                       "transformer", "electrode_arm_end", "motor_manufacturer", "has_balance",
                       "transformer_placement", "flange_pcd", "bracket_direction", "water_circuit",
                       "page", "csrfmiddlewaretoken"] and value:
            dynamic_fields[key] = value

    for field_name, field_value in dynamic_fields.items():
        # 假设动态字段都是文本类型，进行模糊查询
        queryset = queryset.filter(**{f'{field_name}__icontains': field_value})

    log_entry = Log(user=request.user, action_type='search', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=str(query_params))
    log_entry.save()

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_results': paginator.count,
        'query_params': query_params,
    }
    return render(request, 'search_results_en.html', context)


@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # 记录查看详情日志
    log_entry = Log(user=request.user, action_type='view', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Product ID: {product_id}')
    log_entry.save()
    return render(request, 'product_detail.html', {'product': product})

@login_required
def product_detail_en(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    log_entry = Log(user=request.user, action_type='view', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Product ID: {product_id} (English)')
    log_entry.save()
    return render(request, 'product_detail_en.html', {'product': product})


# 新增：检查文件大小的API端点
@login_required
def check_file_size(request, product_id, file_type):
    """检查文件大小是否满足下载条件"""
    try:
        product = get_object_or_404(Product, id=product_id)
        file_path = None
        
        if file_type == 'dwg':
            file_path = product.dwg_file_path
        elif file_type == 'step':
            file_path = product.step_file_path
        elif file_type == 'bmp':
            file_path = product.bmp_file_path

        if not file_path:
            return JsonResponse({
                'can_download': False,
                'message': f'产品没有关联的 {file_type} 文件'
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
                'message': f'文件 {file_type} 不存在或已损坏'
            })
        
        # 获取文件大小（MB）
        file_size_bytes = os.path.getsize(full_file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # 获取或创建用户配置
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # 检查下载限制
        can_download, message = user_profile.can_download_file(file_size_mb)
        
        return JsonResponse({
            'can_download': can_download,
            'message': message,
            'file_size_mb': round(file_size_mb, 2)
        })
        
    except Exception as e:
        return JsonResponse({
            'can_download': False,
            'message': f'检查文件时发生错误: {str(e)}'
        })


@login_required
def download_file(request, product_id, file_type):
    product = get_object_or_404(Product, id=product_id) # 使用 get_object_or_404 避免 Product.DoesNotExist 错误
    file_path = None
    original_filename = None
    
    if file_type == 'dwg':
        file_path = product.dwg_file_path
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
                # 修改：下载失败后返回来源页面，如果是从搜索结果页面来的则返回搜索结果页面
                referer = request.META.get('HTTP_REFERER')
                if referer and 'search_results' in referer:
                    return redirect(referer)
                else:
                    return redirect('clamps:product_detail', product_id=product_id)
            
            # 获取原始文件名（不带路径）
            original_filename = os.path.basename(file_path)
            
            # 对于bmp, dwg, step文件，进行压缩
            if file_type in ['bmp', 'dwg', 'step']:
                # 创建一个临时的内存文件来存储zip内容
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # 获取不带后缀的文件名，并去除特定后缀
                    base_name, ext = os.path.splitext(original_filename)
                    if file_type == 'dwg' and base_name.endswith('_DWG'):
                        base_name = base_name
                    elif file_type == 'step' and base_name.endswith('_STEP'):
                        base_name = base_name
                    elif file_type == 'bmp' and base_name.endswith('_BMP'):
                        base_name = base_name
                    else:
                        # 如果没有特定后缀，则直接使用原始文件名
                        pass
                    
                    # 将文件添加到zip中，使用处理后的文件名
                    zf.write(full_file_path, arcname=original_filename)
                
                zip_buffer.seek(0)
                response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="{base_name}.zip"'
                
                # 记录下载日志
                log_entry = Log(user=request.user, action_type='download', ip_address=request.META.get('REMOTE_ADDR'),
                                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                                details=f'Product ID: {product_id}, File Type: {file_type}, File Size: {file_size_mb:.2f} MB')
                log_entry.save()
                
                return response
            else:
                # 对于其他文件类型，直接提供下载
                with open(full_file_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{original_filename}"'
                    
                    # 记录下载日志
                    log_entry = Log(user=request.user, action_type='download', ip_address=request.META.get('REMOTE_ADDR'),
                                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                                    details=f'Product ID: {product_id}, File Type: {file_type}, File Size: {file_size_mb:.2f} MB')
                    log_entry.save()
                    
                    return response
        else:
            messages.error(request, f"文件 {file_type} 不存在或已损坏")
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
                if file_type == 'dwg':
                    file_path = product.dwg_file_path
                elif file_type == 'step':
                    file_path = product.step_file_path
                elif file_type == 'bmp':
                    file_path = product.bmp_file_path
                elif file_type == 'both':
                    # 对于'both'类型，尝试下载DWG和STEP文件
                    if product.dwg_file_path:
                        files_to_add.append((os.path.join(settings.MEDIA_ROOT, str(product.dwg_file_path).replace('media/', '')), os.path.basename(str(product.dwg_file_path))))
                        total_size_mb += os.path.getsize(os.path.join(settings.MEDIA_ROOT, str(product.dwg_file_path).replace('media/', ''))) / (1024 * 1024)
                    if product.step_file_path:
                        files_to_add.append((os.path.join(settings.MEDIA_ROOT, str(product.step_file_path).replace('media/', '')), os.path.basename(str(product.step_file_path))))
                        total_size_mb += os.path.getsize(os.path.join(settings.MEDIA_ROOT, str(product.step_file_path).replace('media/', ''))) / (1024 * 1024)
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
                        files_to_add.append((full_file_path, os.path.basename(file_path)))
                    else:
                        messages.warning(request, f"文件 {os.path.basename(file_path)} 不存在或已损坏，已跳过。")
                else:
                    messages.warning(request, f"产品 {product.description} 没有关联的 {file_type} 文件，已跳过。")
            
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            can_download, message = user_profile.can_download_file(total_size_mb)
            
            if not can_download:
                messages.error(request, f"批量下载失败：{message}")
                return redirect(request.META.get('HTTP_REFERER', 'clamps:home'))

            for full_path, arcname in files_to_add:
                zf.write(full_path, arcname=arcname)

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="batch_download_{file_type}.zip"'
        
        log_entry = Log(user=request.user, action_type='batch_download', ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        details=f'File Type: {file_type}, Product IDs: {product_ids_str}, Total Size: {total_size_mb:.2f} MB')
        log_entry.save()
        
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
            if file_type == 'dwg':
                file_path = product.dwg_file_path
            elif file_type == 'step':
                file_path = product.step_file_path
            elif file_type == 'bmp':
                file_path = product.bmp_file_path
            elif file_type == 'both':
                # 对于'both'类型，检查DWG和STEP文件大小
                if product.dwg_file_path:
                    full_dwg_path = os.path.join(settings.MEDIA_ROOT, str(product.dwg_file_path).replace('media/', ''))
                    if os.path.exists(full_dwg_path):
                        total_size_mb += os.path.getsize(full_dwg_path) / (1024 * 1024)
                    else:
                        missing_files.append(os.path.basename(str(product.dwg_file_path)))
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
        
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        can_download, message = user_profile.can_download_file(total_size_mb)

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

    # GET 请求处理
    users = User.objects.all().order_by("username")
    users_with_profiles = []

    active_users_count = 0
    admin_users_count = 0

    for user in users:
        profile, created = UserProfile.objects.get_or_create(user=user)
        password_expired = profile.is_password_expired()
        password_expiry_date = profile.get_password_expiry_date()

        if user.is_active:
            active_users_count += 1
        if user.is_staff or user.is_superuser:
            admin_users_count += 1

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
            
            # 创建用户配置，设置默认密码有效期为5天，并保存客户名称
            UserProfile.objects.create(
                user=user, 
                password_validity_days=5, 
                password_last_changed=timezone.now(),
                customer_name=customer_name,
                created_by=request.user
            )
            
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
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)
    writer.writerow(["用户名", "是否激活", "是否员工", "是否超级用户", "注册时间", "客户名称", "密码有效期（天）", "密码最后修改时间", "单次最大下载大小（MB）", "每日最大下载大小（GB）", "每日最大下载文件数", "单次批量下载最大大小（MB）", "创建者"])

    users = User.objects.all().order_by('username')
    for user in users:
        profile, created = UserProfile.objects.get_or_create(user=user)
        created_by_username = profile.created_by.username if profile.created_by else "N/A"
        writer.writerow([
            user.username, 
            user.is_active,
            user.is_staff, 
            user.is_superuser, 
            user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
            profile.customer_name,
            profile.password_validity_days,
            profile.password_last_changed.strftime("%Y-%m-%d %H:%M:%S"),
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
        logs = logs.filter(action_type=action_type)
    if username:
        logs = logs.filter(user__username__icontains=username)
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__lte=date_to + " 23:59:59") # Include the whole day

    logs = logs.order_by("-timestamp")

    total_count = logs.count()
    login_count = logs.filter(action_type='login').count()
    search_count = logs.filter(action_type='search').count()
    download_count = logs.filter(action_type='download').count()
    view_count = logs.filter(action_type='view').count()

    paginator = Paginator(logs, 20)  # 每页显示20条日志
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "total_count": total_count,
        "login_count": login_count,
        "search_count": search_count,
        "download_count": download_count,
        "view_count": view_count,
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
                'ID', 'Category', 'Description', 'Drawing No 1', 'Sub Category Type',
                'Stroke', 'Clamping Force', 'Weight', 'Throat Depth', 'Throat Width',
                'Transformer', 'Electrode Arm End', 'Motor Manufacturer', 'Has Balance',
                'DWG File Path', 'STEP File Path', 'BMP File Path'
            ])
            products = Product.objects.all()
            for product in products:
                writer.writerow([
                    product.id,
                    product.category.name if product.category else '',
                    product.description,
                    product.drawing_no_1,
                    product.sub_category_type,
                    product.stroke,
                    product.clamping_force,
                    product.weight,
                    product.throat_depth,
                    product.throat_width,
                    product.transformer,
                    product.electrode_arm_end,
                    product.motor_manufacturer,
                    product.has_balance,
                    product.dwg_file_path or '',
                    product.step_file_path or '',
                    product.bmp_file_path or ''
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
                writer.writerow([
                    log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
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
@csrf_exempt
def import_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
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

        # 3. 编码检测
        raw_data = csv_file.read()
        try:
            encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
            decoded_file = raw_data.decode(encoding)
        except (UnicodeDecodeError, TypeError):
            try:
                decoded_file = raw_data.decode('gbk')
            except UnicodeDecodeError:
                messages.error(request, '文件编码无法识别，请确保为 UTF-8 或 GBK。')
                return redirect('clamps:import_csv')

        io_string = io.StringIO(decoded_file)
        reader = csv.reader(io_string)
        try:
            next(reader)  # 跳过表头
        except StopIteration:
            messages.error(request, 'CSV 文件为空或没有标题行。')
            return redirect('clamps:import_csv')

        # 4. 预加载现有产品
        existing_products = {p.drawing_no_1.strip().upper(): p for p in Product.objects.all()}

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
                'dwg_file_path': os.path.join('media', row[37].strip()) if len(row) > 37 and row[37].strip() else '',
                'step_file_path': os.path.join('media', row[38].strip()) if len(row) > 38 and row[38].strip() else '',
                'bmp_file_path': os.path.join('media', row[39].strip()) if len(row) > 39 and row[39].strip() else '',
            }

            key = drawing_no_1.upper()
            if key in existing_products:
                # 更新
                product = existing_products[key]
                for k, v in product_data.items():
                    setattr(product, k, v)
                products_to_update.append(product)
                updated_count += 1
            else:
                # 新建
                products_to_create.append(Product(**product_data))
                created_count += 1

        # 6. 批量写入
        with transaction.atomic():
            if products_to_create:
                Product.objects.bulk_create(products_to_create, batch_size=1000)
            if products_to_update:
                Product.objects.bulk_update(
                    products_to_update,
                    fields=list(product_data.keys()),
                    batch_size=1000
                )

        messages.success(
            request,
            f'CSV 导入成功！新增 {created_count} 条，更新 {updated_count} 条。'
        )
        return redirect('clamps:import_csv')

    return render(request, 'management/import_csv.html')

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def sync_files(request):
    if request.method != 'POST':
        return render(request, 'management/sync_files.html')

    media_root = settings.MEDIA_ROOT
    if not os.path.isdir(media_root):
        messages.error(request, f'媒体目录 {media_root} 不存在。')
        return redirect('clamps:management_dashboard')

    # 1. 一次性加载所有产品
    products = Product.objects.all().only(
        'id', 'drawing_no_1',
        'dwg_file_path', 'step_file_path', 'bmp_file_path'
    )
    product_map = {p.drawing_no_1.strip().upper(): p for p in products}

    # 2. 需要批量更新的容器
    to_update = defaultdict(list)

    # 3. 文件后缀 -> 模型字段
    ext_field = {
        '.dwg': 'dwg_file_path',
        '.step': 'step_file_path',
        '.bmp': 'bmp_file_path',
    }

    updated = unmatch = 0
    unmatched_files = []

    # 4. 遍历 media/ 下所有文件
    for root, _, files in os.walk(media_root):
        for filename in files:
            name, ext = os.path.splitext(filename.lower())
            if ext not in ext_field:
                continue

            # 去掉后缀 _dwg/_step/_bmp
            clean = name.upper().replace('_DWG', '').replace('_STEP', '').replace('_BMP', '')
            product = product_map.get(clean)
            if not product:
                unmatch += 1
                unmatched_files.append(filename)
                continue

            field = ext_field[ext]
            # 只保留文件名
            if getattr(product, field) != filename:
                setattr(product, field, filename)
                to_update[field].append(product)
                updated += 1

    # 5. 批量更新
    with transaction.atomic():
        for field, objs in to_update.items():
            Product.objects.bulk_update(objs, [field])

    # 6. 提示
    msg = f'同步完成：更新 {updated} 条记录。'
    if unmatch:
        msg += f' 未匹配 {unmatch} 个文件：{", ".join(unmatched_files[:5])}'
        if len(unmatched_files) > 5:
            msg += ' ...'
    messages.success(request, msg)
    return redirect('clamps:management_dashboard')


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

