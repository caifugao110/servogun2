import zipfile
import io
import os
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
        queryset = queryset.filter(has_balance=True if has_balance == '有' else False)

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
        queryset = queryset.filter(has_balance=True if has_balance == '有' else False)

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
    log_entry = Log(user=request.user, action_type='view_detail', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Product ID: {product_id}')
    log_entry.save()
    return render(request, 'product_detail.html', {'product': product})

@login_required
def product_detail_en(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    log_entry = Log(user=request.user, action_type='view_detail', ip_address=request.META.get('REMOTE_ADDR'),
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
    return render(request, 'management/dashboard.html')

@login_required
@user_passes_test(is_staff_or_superuser)
def manage_users(request):
    users = User.objects.all().order_by('username')
    paginator = Paginator(users, 10)  # 每页显示10个用户
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'management/manage_users.html', {'page_obj': page_obj})

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
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_password = generate_random_password()
        user.set_password(new_password)
        user.save()
        # 更新用户密码过期时间
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        user_profile.password_set_date = timezone.now()
        user_profile.save()
        messages.success(request, f'用户 {user.username} 的密码已重置为: {new_password}')
        return redirect('clamps:manage_users')
    return render(request, 'management/reset_password_confirm.html', {'user': user})

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
        username = request.POST['username']
        password = request.POST['password']
        is_staff = 'is_staff' in request.POST
        is_superuser = 'is_superuser' in request.POST

        if User.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在。')
        else:
            user = User.objects.create_user(username=username, password=password)
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()
            # 设置密码过期时间
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            user_profile.password_set_date = timezone.now()
            user_profile.save()
            messages.success(request, f'用户 {username} 已成功添加。')
            return redirect('clamps:manage_users')
    return render(request, 'management/add_user.html')

@login_required
@user_passes_test(is_staff_or_superuser)
def export_users(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)
    writer.writerow(['Username', 'Email', 'Is Active', 'Is Staff', 'Is Superuser', 'Date Joined'])

    users = User.objects.all().order_by('username')
    for user in users:
        writer.writerow([user.username, user.email, user.is_active, user.is_staff, user.is_superuser, user.date_joined.strftime('%Y-%m-%d %H:%M:%S')])
    return response

@login_required
@user_passes_test(is_staff_or_superuser)
def view_logs(request):
    logs = Log.objects.all().order_by('-timestamp')
    paginator = Paginator(logs, 20)  # 每页显示20条日志
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'management/logs.html', {'page_obj': page_obj})

@login_required
@user_passes_test(is_staff_or_superuser)
def export_data(request):
    if request.method == 'POST':
        data_type = request.POST.get('data_type')
        if data_type == 'products':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="products.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Category', 'Description', 'Drawing No 1', 'Drawing No 2', 'Sub Category Type', 'Stroke', 'Clamping Force', 'Weight', 'Throat Depth', 'Throat Width', 'Transformer', 'Electrode Arm End', 'Motor Manufacturer', 'Has Balance', 'DWG File Path', 'STEP File Path', 'BMP File Path'])
            products = Product.objects.all()
            for product in products:
                writer.writerow([
                    product.id, product.category.name if product.category else '', product.description,
                    product.drawing_no_1, product.drawing_no_2, product.sub_category_type,
                    product.stroke, product.clamping_force, product.weight, product.throat_depth,
                    product.throat_width, product.transformer, product.electrode_arm_end,
                    product.motor_manufacturer, product.has_balance,
                    product.dwg_file_path.name if product.dwg_file_path else '',
                    product.step_file_path.name if product.step_file_path else '',
                    product.bmp_file_path.name if product.bmp_file_path else ''
                ])
            return response
        elif data_type == 'logs':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="logs.csv"'
            writer = csv.writer(response)
            writer.writerow(['Timestamp', 'User', 'Action Type', 'IP Address', 'User Agent', 'Details'])
            logs = Log.objects.all()
            for log in logs:
                writer.writerow([
                    log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    log.user.username if log.user else 'N/A',
                    log.action_type, log.ip_address, log.user_agent, log.details
                ])
            return response
    return render(request, 'management/export_data.html')

@login_required
@user_passes_test(is_staff_or_superuser)
@csrf_exempt # 仅为简化示例，生产环境请使用适当的CSRF保护
def import_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        # 检查文件类型
        if not csv_file.name.endswith('.csv'):
            messages.error(request, '请上传CSV文件。')
            return redirect('clamps:import_csv')

        # 读取文件内容并检测编码
        raw_data = csv_file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding'] if result['encoding'] else 'utf-8'
        
        # 将原始数据解码为字符串，然后用io.StringIO包装
        decoded_file = raw_data.decode(encoding)
        io_string = io.StringIO(decoded_file)
        
        reader = csv.reader(io_string)
        header = next(reader)  # 跳过标题行
        
        created_count = 0
        updated_count = 0
        errors = []

        for i, row in enumerate(reader):
            try:
                # 假设CSV列顺序为: Category, Description, Drawing No 1, Drawing No 2, Sub Category Type, Stroke, Clamping Force, Weight, Throat Depth, Throat Width, Transformer, Electrode Arm End, Motor Manufacturer, Has Balance, DWG File Path, STEP File Path, BMP File Path
                # 确保行有足够的列
                if len(row) < 17:
                    errors.append(f'行 {i+2}: 列数不足，跳过。')
                    continue

                category_name = row[0].strip()
                category, created = Category.objects.get_or_create(name=category_name)

                product_data = {
                    'category': category,
                    'description': row[1].strip(),
                    'drawing_no_1': row[2].strip(),
                    'drawing_no_2': row[3].strip(),
                    'sub_category_type': row[4].strip(),
                    'stroke': float(row[5].strip()) if row[5].strip() else None,
                    'clamping_force': float(row[6].strip()) if row[6].strip() else None,
                    'weight': float(row[7].strip()) if row[7].strip() else None,
                    'throat_depth': float(row[8].strip()) if row[8].strip() else None,
                    'throat_width': float(row[9].strip()) if row[9].strip() else None,
                    'transformer': row[10].strip(),
                    'electrode_arm_end': row[11].strip(),
                    'motor_manufacturer': row[12].strip(),
                    'has_balance': row[13].strip().lower() == 'true' if row[13].strip() else False,
                }
                
                # 处理文件路径，确保它们是相对路径，并指向MEDIA_ROOT下的文件
                # 注意：这里假设CSV中提供的路径是相对于MEDIA_ROOT的，或者是不带media/前缀的
                dwg_file_name = row[14].strip()
                step_file_name = row[15].strip()
                bmp_file_name = row[16].strip()

                # 构建相对路径，如果CSV中提供的是文件名，则直接使用
                # 如果CSV中提供了完整的media/路径，则需要处理
                product_data['dwg_file_path'] = os.path.join('media', dwg_file_name) if dwg_file_name else ''
                product_data['step_file_path'] = os.path.join('media', step_file_name) if step_file_name else ''
                product_data['bmp_file_path'] = os.path.join('media', bmp_file_name) if bmp_file_name else ''

                # 尝试根据 drawing_no_1 更新现有产品，否则创建新产品
                product, created = Product.objects.update_or_create(
                    drawing_no_1=product_data['drawing_no_1'],
                    defaults=product_data
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                errors.append(f'行 {i+2} 处理失败: {e}')

        if not errors:
            messages.success(request, f'CSV导入成功！新增 {created_count} 条，更新 {updated_count} 条。')
        else:
            messages.warning(request, f'CSV导入完成，但存在 {len(errors)} 个错误。新增 {created_count} 条，更新 {updated_count} 条。')
            for error in errors:
                messages.error(request, error)

        return redirect('clamps:import_csv')
    return render(request, 'management/import_csv.html')

@login_required
@user_passes_test(is_staff_or_superuser)
def sync_files(request):
    if request.method == 'POST':
        # 假设所有文件都存储在 MEDIA_ROOT/media/ 目录下
        media_dir = os.path.join(settings.MEDIA_ROOT, 'media')
        if not os.path.exists(media_dir):
            messages.error(request, f"媒体目录 {media_dir} 不存在。")
            return redirect('clamps:management_dashboard')

        # 遍历所有产品，检查文件路径是否存在
        products = Product.objects.all()
        synced_count = 0
        missing_count = 0
        
        for product in products:
            files_to_check = [
                product.dwg_file_path,
                product.step_file_path,
                product.bmp_file_path,
            ]
            
            for file_field in files_to_check:
                if file_field and file_field.name:
                    # 构建完整的文件系统路径
                    full_path = os.path.join(settings.MEDIA_ROOT, file_field.name)
                    if os.path.exists(full_path):
                        synced_count += 1
                    else:
                        missing_count += 1
                        # 可以选择在这里记录缺失的文件或采取其他措施
                        print(f"Missing file: {full_path} for product {product.drawing_no_1}")
        
        messages.success(request, f"文件同步检查完成。找到 {synced_count} 个文件，发现 {missing_count} 个缺失文件。")
        return redirect('clamps:management_dashboard')
    return render(request, 'management/sync_files.html')


