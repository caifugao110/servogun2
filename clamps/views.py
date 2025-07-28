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
    return redirect('clamps:home')


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
                        base_name = base_name[:-4] # Remove _DWG
                    elif file_type == 'step' and base_name.endswith('_STEP'):
                        base_name = base_name[:-5] # Remove _STEP
                    
                    # 构建新的文件名
                    new_filename_in_zip = f"{base_name}{ext}"

                    # 将原始文件添加到zip中，使用新的文件名
                    zf.write(full_file_path, new_filename_in_zip)
                
                # 设置zip文件的下载名称
                zip_filename = f"{base_name}.zip" # 压缩包的名称也应该去除后缀
                
                response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            else:
                # 其他文件类型按原样下载
                with open(full_file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{original_filename}"'
            
            # 记录下载统计
            user_profile.record_download(file_size_mb)
            
            # 记录下载日志
            log_entry = Log(user=request.user, action_type='download', ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Downloaded {file_type} for Product ID: {product_id}, Size: {file_size_mb:.2f}MB')
            log_entry.save()
            return response
        else:
            messages.error(request, f"文件 {file_type} 不存在或已损坏。尝试从路径: {full_file_path}")
            messages.error(request, f"产品没有关联的 {file_type} 文件。")
    else:
        messages.error(request, f"产品没有关联的 {file_type} 文件。")
    
    # 修改：下载失败后返回来源页面，如果是从搜索结果页面来的则返回搜索结果页面
    referer = request.META.get('HTTP_REFERER')
    if referer and 'search_results' in referer:
        return redirect(referer)
    else:
        return redirect('clamps:product_detail', product_id=product_id)


# 新增：检查批量下载文件大小的API端点
@login_required
def check_batch_file_size(request):
    """检查批量下载文件大小是否满足下载条件"""
    try:
        file_type = request.GET.get('file_type', 'step')  # 默认step
        product_ids_str = request.GET.get('ids', '')
        
        if not product_ids_str:
            return JsonResponse({
                'can_download': False,
                'message': '未选择任何产品进行下载'
            })

        product_ids = []
        for pid in product_ids_str.split(','):
            try:
                product_ids.append(int(pid))
            except ValueError:
                continue

        if not product_ids:
            return JsonResponse({
                'can_download': False,
                'message': '无效的产品ID列表'
            })

        # 获取或创建用户配置
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        total_download_size_mb = 0
        file_count = 0

        for product_id in product_ids:
            try:
                product = get_object_or_404(Product, id=product_id)
                
                # 根据 file_type 收集文件路径和大小
                if file_type == 'dwg' or file_type == 'both':
                    if product.dwg_file_path:
                        relative_path = str(product.dwg_file_path)
                        if relative_path.startswith('media/'):
                            relative_path = relative_path[len('media/'):]
                        elif relative_path.startswith('/media/'):
                            relative_path = relative_path[len('/media/'):]
                        full_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                        if os.path.exists(full_file_path):
                            file_size_bytes = os.path.getsize(full_file_path)
                            total_download_size_mb += (file_size_bytes / (1024 * 1024))
                            file_count += 1

                if file_type == 'step' or file_type == 'both':
                    if product.step_file_path:
                        relative_path = str(product.step_file_path)
                        if relative_path.startswith('media/'):
                            relative_path = relative_path[len('media/'):]
                        elif relative_path.startswith('/media/'):
                            relative_path = relative_path[len('/media/'):]
                        full_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                        if os.path.exists(full_file_path):
                            file_size_bytes = os.path.getsize(full_file_path)
                            total_download_size_mb += (file_size_bytes / (1024 * 1024))
                            file_count += 1

            except Product.DoesNotExist:
                continue
            except Exception:
                continue

        if file_count == 0:
            return JsonResponse({
                'can_download': False,
                'message': '没有找到任何可下载的文件'
            })

        # 检查批量下载限制
        can_download, message = user_profile.can_download_file(total_download_size_mb, is_batch=True)
        
        return JsonResponse({
            'can_download': can_download,
            'message': message,
            'total_size_mb': round(total_download_size_mb, 2),
            'file_count': file_count
        })
        
    except Exception as e:
        return JsonResponse({
            'can_download': False,
            'message': f'检查文件时发生错误: {str(e)}'
        })


@login_required
def batch_download_view(request, file_type):
    """
    处理批量下载请求的视图函数。
    根据 file_type 和 ids 参数，打包并返回相应的文件。
    """
    product_ids_str = request.GET.get('ids')
    if not product_ids_str:
        messages.error(request, "未选择任何产品进行下载。")
        # 修改：下载失败后返回来源页面，通常是搜索结果页面
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        else:
            return redirect('clamps:search_results')

    product_ids = []
    for pid in product_ids_str.split(','):
        try:
            product_ids.append(int(pid))
        except ValueError:
            continue # 忽略无效的ID

    if not product_ids:
        messages.error(request, "无效的产品ID列表。")
        # 修改：下载失败后返回来源页面，通常是搜索结果页面
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        else:
            return redirect('clamps:search_results')

    # 获取或创建用户配置
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    total_download_size_mb = 0
    files_to_zip = []

    for product_id in product_ids:
        try:
            product = get_object_or_404(Product, id=product_id)
            
            # 根据 file_type 收集文件路径和大小
            if file_type == 'dwg' or file_type == 'both':
                if product.dwg_file_path:
                    relative_path = str(product.dwg_file_path)
                    if relative_path.startswith('media/'):
                        relative_path = relative_path[len('media/'):]
                    elif relative_path.startswith('/media/'):
                        relative_path = relative_path[len('/media/'):]
                    full_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                    if os.path.exists(full_file_path):
                        file_size_bytes = os.path.getsize(full_file_path)
                        total_download_size_mb += (file_size_bytes / (1024 * 1024))
                        files_to_zip.append({'path': full_file_path, 'type': 'dwg', 'product': product})

            if file_type == 'step' or file_type == 'both':
                if product.step_file_path:
                    relative_path = str(product.step_file_path)
                    if relative_path.startswith('media/'):
                        relative_path = relative_path[len('media/'):]
                    elif relative_path.startswith('/media/'):
                        relative_path = relative_path[len('/media/'):]
                    full_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                    if os.path.exists(full_file_path):
                        file_size_bytes = os.path.getsize(full_file_path)
                        total_download_size_mb += (file_size_bytes / (1024 * 1024))
                        files_to_zip.append({'path': full_file_path, 'type': 'step', 'product': product})

        except Product.DoesNotExist:
            messages.warning(request, f"产品ID {product_id} 不存在。")
            continue
        except Exception as e:
            messages.error(request, f"处理产品ID {product_id} 时发生错误: {e}")
            continue

    # 检查批量下载限制
    can_download, message = user_profile.can_download_file(total_download_size_mb, is_batch=True)
    if not can_download:
        messages.error(request, f"批量下载失败：{message}")
        # 修改：下载失败后返回来源页面，通常是搜索结果页面
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        else:
            return redirect('clamps:search_results')

    # 创建一个内存中的 ZIP 文件
    zip_buffer = io.BytesIO()
    zip_file_name = f"selected_clamps_{file_type}_{timezone.now().strftime('%Y%m%d%H%M%S')}.zip"

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        downloaded_count = 0
        for file_info in files_to_zip:
            full_file_path = file_info['path']
            file_type_single = file_info['type']
            product = file_info['product']
            drawing_no = product.drawing_no_1 if product.drawing_no_1 else f"product_{product.id}"

            # 获取原始文件名（不带路径）
            original_file_basename = os.path.basename(full_file_path)
            base_name, ext = os.path.splitext(original_file_basename)
            
            # 去除特定后缀
            if file_type_single == 'dwg' and base_name.endswith('_DWG'):
                base_name = base_name[:-4]
            elif file_type_single == 'step' and base_name.endswith('_STEP'):
                base_name = base_name[:-5]
            
            # 使用新的文件名作为ZIP文件中的文件名
            arcname = f"{base_name}{ext}" 
            zf.write(full_file_path, arcname=arcname)
            downloaded_count += 1

    zip_buffer.seek(0)
    
    if downloaded_count == 0:
        messages.error(request, "没有找到任何可下载的文件。")
        # 修改：下载失败后返回来源页面，通常是搜索结果页面
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        else:
            return redirect('clamps:search_results')

    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_file_name}"'
    
    # 记录批量下载日志
    log_entry = Log(user=request.user, action_type='batch_download', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details=f'批量下载了 {downloaded_count} 个 {file_type} 文件，产品ID: {product_ids_str}, 总大小: {total_download_size_mb:.2f}MB')
    log_entry.save()
    
    # 记录下载统计
    user_profile.record_download(total_download_size_mb)
    
    return response


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
        user_id = request.POST.get('user_id')
        
        if action == 'activate':
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            log_entry = Log(user=request.user, action_type='activate_user', ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'User {user.username} activated')
            log_entry.save()
            messages.success(request, f'用户 {user.username} 已激活')
            
        elif action == 'deactivate':
            user = User.objects.get(id=user_id)
            user.is_active = False
            user.save()
            log_entry = Log(user=request.user, action_type='deactivate_user', ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'User {user.username} deactivated')
            log_entry.save()
            messages.success(request, f'用户 {user.username} 已停用')
            
        elif action == 'update_config':
            user = User.objects.get(id=user_id)
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            
            # 更新密码有效期设置
            password_validity = request.POST.get('password_validity_days')
            if password_validity:
                new_validity_days = int(password_validity)
                old_validity_days = user_profile.password_validity_days
                
                # 如果密码已过期且设置了新的有效期（非永久），则重置密码状态
                if user_profile.is_password_expired() and new_validity_days > 0:
                    # 重置密码最后修改时间为当前时间，使密码重新生效
                    user_profile.password_last_changed = timezone.now()
                    messages.info(request, f'用户 {user.username} 的密码状态已重置，新的有效期为 {new_validity_days} 天')
                
                user_profile.password_validity_days = new_validity_days
            
            # 更新下载限制设置
            max_single_download = request.POST.get('max_single_download_mb')
            if max_single_download:
                user_profile.max_single_download_mb = int(max_single_download)
                
            max_daily_download_gb = request.POST.get('max_daily_download_gb')
            if max_daily_download_gb:
                user_profile.max_daily_download_gb = int(max_daily_download_gb)
                
            max_daily_download_count = request.POST.get('max_daily_download_count')
            if max_daily_download_count:
                user_profile.max_daily_download_count = int(max_daily_download_count)
            
            # 添加批量下载限制设置
            max_batch_download_mb = request.POST.get('max_batch_download_mb')
            if max_batch_download_mb:
                user_profile.max_batch_download_mb = int(max_batch_download_mb)
            
            # 更新用户信息
            customer_name = request.POST.get('customer_name')
            if customer_name is not None:  # 允许空字符串
                user_profile.customer_name = customer_name.strip()
            
            email = request.POST.get('email')
            if email is not None:  # 允许空字符串
                user.email = email.strip()
            
            password_remark = request.POST.get('password_remark')
            if password_remark is not None:  # 允许空字符串
                # 将密码备注存储到first_name和last_name字段
                remark_parts = password_remark.strip().split(' ', 1)
                user.first_name = remark_parts[0] if remark_parts else ''
                user.last_name = remark_parts[1] if len(remark_parts) > 1 else ''
            
            user.save()
            user_profile.save()
            
            log_entry = Log(user=request.user, action_type='update_user_config', ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Updated config for user {user.username}')
            log_entry.save()
            messages.success(request, f'用户 {user.username} 的配置已更新')
        
        return redirect('clamps:manage_users')
    
    # 获取所有用户及其配置
    # 如果当前用户是超级管理员，显示所有用户
    # 如果当前用户是管理员，只显示普通用户
    if request.user.is_superuser:
        users = User.objects.all().order_by('username')
    else: # is_staff == True
        users = User.objects.filter(is_staff=False, is_superuser=False).order_by('username')

    users_with_profiles = []
    
    for user in users:
        profile, created = UserProfile.objects.get_or_create(user=user)
        users_with_profiles.append({
            'user': user,
            'profile': profile,
            'password_expired': profile.is_password_expired(),
            'password_expiry_date': profile.get_password_expiry_date()
        })
    
    context = {
        'users_with_profiles': users_with_profiles,
        'password_validity_choices': UserProfile.get_password_validity_choices()
    }
    return render(request, 'management/users.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def toggle_user_active(request, user_id):
    user = User.objects.get(id=user_id)
    user.is_active = not user.is_active
    user.save()
    log_entry = Log(user=request.user, action_type='toggle_user_active', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'User {user.username} active status toggled to {user.is_active}')
    log_entry.save()
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
    user = User.objects.get(id=user_id)
    username = user.username
    user.delete()
    log_entry = Log(user=request.user, action_type='delete_user', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'User {username} deleted.')
    log_entry.save()
    return redirect('clamps:manage_users')


@login_required
@user_passes_test(is_staff_or_superuser)
def view_logs(request):
    logs = Log.objects.all().order_by('-timestamp')

    action_type = request.GET.get('action_type')
    username = request.GET.get('username')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if action_type and action_type != 'all':
        logs = logs.filter(action_type=action_type)
    if username:
        logs = logs.filter(user__username__icontains=username)
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        # 结束日期增加一天，以包含选择日期的整天
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        date_to_inclusive = date_to_obj + timedelta(days=1)
        logs = logs.filter(timestamp__lt=date_to_inclusive)
    total_count = logs.count()

    # 统计各项操作的次数
    login_count = logs.filter(action_type='login').count()
    search_count = logs.filter(action_type='search').count()
    download_count = logs.filter(action_type='download').count()
    view_count = logs.filter(action_type='view').count()

    paginator = Paginator(logs, 50)  # 每页50条记录
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_count': total_count,
        'login_count': login_count,
        'search_count': search_count,
        'download_count': download_count,
        'view_count': view_count,
    }
    return render(request, 'management/logs.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def export_data(request):
    if request.method == 'POST':
        export_type = request.POST.get('export_type')
        
        if export_type == 'products':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="products.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['ID', '分类', '描述', '图号1', '子分类类型', '行程', '电极臂端部', '加压力', '电极臂', '变压器', '重量'])
            
            for product in Product.objects.all():
                writer.writerow([
                    product.id,
                    product.category.name if product.category else '',
                    product.description or '',
                    product.drawing_no_1 or '',
                    product.sub_category_type or '',
                    product.stroke or '',
                    product.electrode_arm_end or '',
                    product.clamping_force or '',
                    product.electrode_arm_type or '',
                    product.transformer or '',
                    product.weight or ''
                ])
            
            filename = 'products.csv'
        
        elif export_type == 'users':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="users.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['ID', '用户名', '邮箱', '姓名', '是否活跃', '是否管理员', '注册时间', '最后登录'])
            
            for user in User.objects.all():
                writer.writerow([
                    user.id,
                    user.username,
                    user.email or '',
                    f"{user.first_name} {user.last_name}".strip() or '',
                    '是' if user.is_active else '否',
                    '是' if user.is_staff else '否',
                    user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                    user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '从未登录'
                ])
            
            filename = 'users.csv'
        
        elif export_type == 'logs':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="logs.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['ID', '用户', '操作类型', '详情', '时间', 'IP地址', '用户代理'])
            
            # 获取筛选条件
            action_type = request.POST.get('action_type')
            username = request.POST.get('username')
            date_from = request.POST.get('date_from')
            date_to = request.POST.get('date_to')

            export_logs = Log.objects.all().order_by('-timestamp')

            if action_type and action_type != 'all':
                export_logs = export_logs.filter(action_type=action_type)
            if username:
                export_logs = export_logs.filter(user__username__icontains=username)
            if date_from:
                export_logs = export_logs.filter(timestamp__gte=date_from)
            if date_to:
                export_logs = export_logs.filter(timestamp__lte=date_to)

            for log in export_logs:
                writer.writerow([
                    log.id,
                    log.user.username if log.user else '匿名',
                    log.action_type,
                    log.details or '',
                    log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    log.ip_address or '',
                    log.user_agent or ''
                ])
            
            filename = 'logs.csv'
        
        # 记录导出日志
        log_entry = Log(user=request.user, action_type='export_data', ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Exported {export_type} data')
        log_entry.save()
        
        return response
    
    return render(request, 'management/export.html')


@login_required
@user_passes_test(is_staff_or_superuser)
def import_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        # 检测文件编码
        raw_data = csv_file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        
        # 重置文件指针
        csv_file.seek(0)
        
        try:
            # 使用检测到的编码读取文件
            decoded_file = csv_file.read().decode(encoding)
            csv_reader = csv.DictReader(io.StringIO(decoded_file))
            
            imported_count = 0
            for row in csv_reader:
                # 这里需要根据实际的CSV格式来处理数据
                # 示例代码，需要根据实际情况修改
                try:
                    category_name = row.get('分类', '').strip()
                    if category_name:
                        category, created = Category.objects.get_or_create(name=category_name)
                    else:
                        category = None
                    
                    product = Product(
                        category=category,
                        description=row.get('描述', '').strip() or None,
                        drawing_no_1=row.get('图号1', '').strip() or None,
                        sub_category_type=row.get('子分类类型', '').strip() or None,
                    )
                    
                    # 处理数值字段
                    for field in ['stroke', 'clamping_force', 'weight', 'throat_depth', 'throat_width']:
                        value = row.get(field, '').strip()
                        if value:
                            try:
                                setattr(product, field, float(value))
                            except ValueError:
                                pass
                    
                    # 处理文本字段
                    for field in ['electrode_arm_end', 'electrode_arm_type', 'transformer', 'transformer_placement']:
                        value = row.get(field, '').strip()
                        if value:
                            setattr(product, field, value)
                    
                    product.save()
                    imported_count += 1
                    
                except Exception as e:
                    messages.warning(request, f"导入行时出错: {e}")
                    continue
            
            messages.success(request, f"成功导入 {imported_count} 条记录")
            
            # 记录导入日志
            log_entry = Log(user=request.user, action_type='import_csv', ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Imported {imported_count} records from CSV')
            log_entry.save()
            
        except Exception as e:
            messages.error(request, f"导入失败: {e}")
    
    return render(request, 'management/import_csv.html')


@login_required
@user_passes_test(is_staff_or_superuser)
def sync_files(request):
    if request.method == 'POST':
        media_root = settings.MEDIA_ROOT
        synced_count = 0
        
        # 遍历所有产品，检查文件路径
        for product in Product.objects.all():
            updated = False
            
            # 检查DWG文件
            if product.dwg_file_path:
                full_path = os.path.join(media_root, product.dwg_file_path.lstrip('/media/'))
                if not os.path.exists(full_path):
                    product.dwg_file_path = None
                    updated = True
            
            # 检查STEP文件
            if product.step_file_path:
                full_path = os.path.join(media_root, product.step_file_path.lstrip('/media/'))
                if not os.path.exists(full_path):
                    product.step_file_path = None
                    updated = True
            
            # 检查BMP文件
            if product.bmp_file_path:
                full_path = os.path.join(media_root, product.bmp_file_path.lstrip('/media/'))
                if not os.path.exists(full_path):
                    product.bmp_file_path = None
                    updated = True
            
            if updated:
                product.save()
                synced_count += 1
        
        messages.success(request, f"文件同步完成，更新了 {synced_count} 个产品的文件路径")
        
        # 记录同步日志
        log_entry = Log(user=request.user, action_type='sync_files', ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Synced {synced_count} product file paths')
        log_entry.save()
        
        return redirect('clamps:management_dashboard')
    
    return render(request, 'management/dashboard.html')






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
                customer_name=customer_name
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
@user_passes_test(is_superuser)
def export_users(request):
    """导出所有用户信息为CSV文件"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    
    # 添加BOM以支持Excel正确显示中文
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow(['用户ID', '用户名', '客户名称', '邮箱', '密码备注', '状态', '权限', '密码有效期', '单次下载限制(MB)', '批量下载限制(MB)', '每日下载限制(GB)', '每日下载文件数限制', '注册时间', '最后登录'])
    
    for user in User.objects.all().order_by('id'):
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # 确定用户权限
        if user.is_superuser:
            permission = '超级管理员'
        elif user.is_staff:
            permission = '管理员'
        else:
            permission = '普通用户'
        
        # 确定密码有效期
        if profile.password_validity_days == 0:
            password_validity = '永久有效'
        else:
            password_validity = f'{profile.password_validity_days}天'
        
        writer.writerow([
            user.id,
            user.username,
            profile.customer_name or '',
            user.email or '',
            f"{user.first_name} {user.last_name}".strip() or '',
            '活跃' if user.is_active else '停用',
            permission,
            password_validity,
            profile.max_single_download_mb,
            profile.max_batch_download_mb,
            profile.max_daily_download_gb,
            profile.max_daily_download_count,
            user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '从未登录'
        ])
    
    # 记录导出日志
    log_entry = Log(
        user=request.user, 
        action_type='export_users', 
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''), 
        details='Exported all users information'
    )
    log_entry.save()
    
    return response



