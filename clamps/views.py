from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import csv
import chardet
import io
import os
from django.conf import settings

from .models import Category, Product, Log

def is_admin(user):
    return user.is_superuser


def home(request):
    return render(request, 'home.html')


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # 记录登录日志
            log_entry = Log(user=user, action_type='login', ip_address=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', ''))
            log_entry.save()
            return redirect('clamps:home')
        else:
            return render(request, 'login.html', {'error': '无效的用户名或密码'})
    return render(request, 'login.html')


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
def product_detail(request, product_id):
    product = Product.objects.get(id=product_id)
    # 记录查看详情日志
    log_entry = Log(user=request.user, action_type='view_detail', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Product ID: {product_id}')
    log_entry.save()
    return render(request, 'product_detail.html', {'product': product})


@login_required
def download_file(request, product_id, file_type):
    product = Product.objects.get(id=product_id)
    file_path = None
    
    # 修复：使用正确的文件路径字段
    if file_type == 'dwg':
        file_path = product.dwg_file_path
    elif file_type == 'step':
        file_path = product.step_file_path
    elif file_type == 'bmp':
        file_path = product.bmp_file_path

    if file_path:
        # 确保 file_path 是相对于 MEDIA_ROOT 的路径
        if file_path.startswith('media/'):
            file_path = file_path[len('media/'):]
        elif file_path.startswith('/media/'):
            file_path = file_path[len('/media/'):]

        full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        if os.path.exists(full_file_path):
            with open(full_file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type="application/octet-stream")
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                # 记录下载日志
                log_entry = Log(user=request.user, action_type='download', ip_address=request.META.get('REMOTE_ADDR'),
                                user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Downloaded {file_type} for Product ID: {product_id}')
                log_entry.save()
                return response
        else:
            messages.error(request, f"文件 {file_type} 不存在或已损坏。尝试从路径: {full_file_path}")
            messages.error(request, f"产品没有关联的 {file_type} 文件。")
    
    # 获取来源页面的查询参数，用于重定向回原搜索结果页面
    referer = request.META.get('HTTP_REFERER', '')
    if 'search/results/' in referer:
        # 如果来自搜索结果页面，重定向回原页面
        return redirect(referer)
    else:
        # 否则重定向到搜索结果页面
        return redirect('clamps:search_results')


@login_required
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
def manage_users(request):
    users = User.objects.all().order_by('username')
    context = {
        'users': users
    }
    return render(request, 'management/users.html', context)


@login_required
@user_passes_test(is_admin)
def toggle_user_active(request, user_id):
    user = User.objects.get(id=user_id)
    user.is_active = not user.is_active
    user.save()
    log_entry = Log(user=request.user, action_type='toggle_user_active', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'User {user.username} active status toggled to {user.is_active}')
    log_entry.save()
    return redirect('clamps:manage_users')


@login_required
@user_passes_test(is_admin)
def reset_user_password(request, user_id):
    user = User.objects.get(id=user_id)
    new_password = User.objects.make_random_password()
    user.set_password(new_password)
    user.save()
    log_entry = Log(user=request.user, action_type='reset_user_password', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'User {user.username} password reset. New password: {new_password}')
    log_entry.save()
    return render(request, 'management/users.html', {'users': User.objects.all(), 'message': f'用户 {user.username} 的新密码是: {new_password}'})


@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    user = User.objects.get(id=user_id)
    username = user.username
    user.delete()
    log_entry = Log(user=request.user, action_type='delete_user', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'User {username} deleted.')
    log_entry.save()
    return redirect('clamps:manage_users')


@login_required
@user_passes_test(is_admin)
def view_logs(request):
    logs = Log.objects.all().order_by("-timestamp")

    # Apply filters
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
        logs = logs.filter(timestamp__lte=date_to)

    total_count = logs.count() # Get total count before pagination

    paginator = Paginator(logs, 50)  # 每页50条日志
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
        "total_count": total_count, # Pass total count to template
        "login_count": Log.objects.filter(action_type="login").count(),
        "search_count": Log.objects.filter(action_type="search").count(),
        "download_count": Log.objects.filter(action_type="download").count(),
        "view_count": Log.objects.filter(action_type="view").count(),
    }
    return render(request, "management/logs.html", context)


@login_required
@user_passes_test(is_admin)
def export_data(request):
    if request.method == 'POST':
        data_type = request.POST.get('data_type')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{data_type}_export_{timezone.now().strftime("%Y%m%d%H%M%S")}.csv"'

        writer = csv.writer(response)

        if data_type == 'products':
            writer.writerow(["ID", "Category", "Description", "Drawing No 1", "Sub Category Type", "Stroke", "Clamping Force", "Weight", "Throat Depth", "Throat Width", "Transformer", "Electrode Arm End", "Motor Manufacturer", "Has Balance", "Water Circuit", "Bracket Direction", "Bracket Angle", "Bracket Count", "Gearbox Type", "Bracket Material", "Gearbox Stroke", "Tool Changer", "Static Arm Eccentricity", "Static Electrode Arm End", "Moving Arm Eccentricity", "Moving Electrode Arm End", "Pivot to Drive Center Dist", "Static Arm Front Length", "Static Arm Front Height", "Moving Arm Front Length", "Moving Arm Front Height", "Eccentricity to Center", "Grip Extension Length", "Eccentricity", "Eccentricity Direction", "Guidance Method", "DWG File Path", "STEP File Path", "BMP File Path"])
            for product in Product.objects.all():
                writer.writerow([
                    product.id, product.category.name, product.description, product.drawing_no_1, product.sub_category_type,
                    product.stroke, product.clamping_force, product.weight, product.throat_depth, product.throat_width, product.transformer,
                    product.electrode_arm_end, product.motor_manufacturer, product.has_balance, product.water_circuit, product.bracket_direction,
                    product.bracket_angle, product.bracket_count, product.gearbox_type, product.bracket_material, product.gearbox_stroke,
                    product.tool_changer, product.static_arm_eccentricity, product.static_electrode_arm_end, product.moving_arm_eccentricity,
                    product.moving_electrode_arm_end, product.pivot_to_drive_center_dist, product.static_arm_front_length,
                    product.static_arm_front_height, product.moving_arm_front_length, product.moving_arm_front_height,
                    product.eccentricity_to_center, product.grip_extension_length, product.eccentricity, product.eccentricity_direction,
                    product.guidance_method, product.dwg_file_path, product.step_file_path, product.bmp_file_path
                ])
        elif data_type == 'users':
            writer.writerow(['ID', 'Username', 'Email', 'Is Active', 'Is Superuser', 'Date Joined', 'Last Login'])
            for user in User.objects.all():
                writer.writerow([
                    user.id, user.username, user.email, user.is_active, user.is_superuser, user.date_joined, user.last_login
                ])
        elif data_type == 'logs':
            writer.writerow(['ID', 'Timestamp', 'User', 'action_type', 'IP Address', 'User Agent', 'Details'])
            for log in Log.objects.all():
                writer.writerow([
                    log.id, log.timestamp, log.user.username if log.user else 'N/A', log.action_type, log.ip_address, log.user_agent, log.details
                ])
        
        log_entry = Log(user=request.user, action_type='export_data', ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''), details=f'Exported {data_type} data.')
        log_entry.save()
        return response
    return render(request, 'management/export.html')


@login_required
@user_passes_test(is_admin)
@csrf_exempt # 暂时禁用CSRF，方便测试，生产环境请启用
def import_csv(request):
    if request.method == 'POST' and request.FILES['csv_file']:
        csv_file = request.FILES['csv_file']
        file_data = csv_file.read()
        # 检测文件编码
        result = chardet.detect(file_data)
        encoding = result['encoding'] if result['encoding'] else 'utf-8'

        decoded_file = file_data.decode(encoding).splitlines()
        reader = csv.DictReader(decoded_file)

        updated_count = 0
        created_count = 0
        errors = []

        # 字段映射，CSV表头到模型字段
        field_mapping = {
            '描述': 'description',
            '图号1(o)': 'drawing_no_1',
            '子分类类型': 'sub_category_type',
            '行程': 'stroke',
            '加压力': 'clamping_force',
            '重量': 'weight',
            '喉深': 'throat_depth',
            '喉宽': 'throat_width',
            '变压器': 'transformer',
            '电极臂端部': 'electrode_arm_end',
            '电极臂类型': 'electrode_arm_type',
            '变压器放置方向': 'transformer_placement',
            '法兰盘P.C.D': 'flange_pcd',
            '分类': 'sub_category_type',
            'X2C-V2-C型分类': 'sub_category_type',
            'X2C-V3-C型分类': 'sub_category_type',
            'X2C-X型分类': 'sub_category_type',
            'X2C-V2-X型分类': 'sub_category_type',
            'X2C-V3-X型分类': 'sub_category_type',
            'X2C-C型分类': 'sub_category_type',
            '有无平衡': 'has_balance',
            '水路': 'water_circuit',
            '托架方向': 'bracket_direction',
            '托架角度': 'bracket_angle',
            'MOTOR厂家': 'motor_manufacturer',
            '托架个数': 'bracket_count',
            '齿轮箱型式': 'gearbox_type',
            '托架材料': 'bracket_material',
            '齿轮箱行程': 'gearbox_stroke',
            '换枪装置': 'tool_changer',
            # X型分类独有参数
            '静臂偏心': 'static_arm_eccentricity',
            '静电极臂端部': 'static_electrode_arm_end',
            '动臂偏心': 'moving_arm_eccentricity',
            '动电极臂端部': 'moving_electrode_arm_end',
            '支轴到驱动中心距离': 'pivot_to_drive_center_dist',
            '静电极臂前部长': 'static_arm_front_length',
            '静电极臂前部高': 'static_arm_front_height',
            '动电极臂前部长': 'moving_arm_front_length',
            '动电极臂前部高': 'moving_arm_front_height',
            '偏心是否回到中心面': 'eccentricity_to_center',
            '握杆伸出长度': 'grip_extension_length',
            '偏心': 'eccentricity',
            '偏心方向': 'eccentricity_direction',
            '导向方式': 'guidance_method',
        }

        # 获取分类信息，用于关联产品
        category_name = csv_file.name.split('.')[0] # 假设文件名就是分类名，例如X2C-C
        try:
            category = Category.objects.get(name=category_name)
        except Category.DoesNotExist:
            messages.error(request, f"分类 '{category_name}' 不存在。请先创建该分类。")
            return render(request, 'management/import_csv.html', {'errors': errors})

        for row in reader:
            drawing_no_1 = row.get('图号1(o)')
            if not drawing_no_1:
                errors.append(f"跳过缺少'图号1(o)'的行: {row}")
                continue

            product_data = {'category': category}
            for csv_header, model_field in field_mapping.items():
                value = row.get(csv_header)
                if value is not None:
                    # 处理空字符串为None，以便模型字段的null=True生效
                    if value == '':
                        product_data[model_field] = None
                    else:
                        # 尝试转换数字类型字段
                        if model_field in ["stroke", "clamping_force", "weight", "throat_depth", "throat_width", "bracket_count", "eccentricity", "static_arm_eccentricity", "moving_arm_eccentricity", "pivot_to_drive_center_dist", "static_arm_front_length", "static_arm_front_height", "moving_arm_front_length", "moving_arm_front_height", "grip_extension_length", "bracket_angle"]:
                            try:
                                product_data[model_field] = float(value)
                            except ValueError:
                                errors.append(f"行 {drawing_no_1}: 字段 '{csv_header}' 的值 '{value}' 不是有效的数字。")
                                product_data[model_field] = None # 设置为None或跳过，取决于业务需求
                        elif model_field == 'has_balance':
                            product_data[model_field] = (value.lower() == '有')
                        else:
                            product_data[model_field] = value

            try:
                product, created = Product.objects.update_or_create(
                    drawing_no_1=drawing_no_1,
                    defaults=product_data
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                errors.append(f"处理行 {drawing_no_1} 时发生错误: {e}")

        log_entry = Log(user=request.user, action_type='import_csv', ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        details=f'Imported CSV: {csv_file.name}. Created: {created_count}, Updated: {updated_count}, Errors: {len(errors)}.')
        log_entry.save()

        if not errors:
            messages.success(request, f"CSV文件 '{csv_file.name}' 导入成功！新增 {created_count} 条，更新 {updated_count} 条记录。")
        else:
            messages.warning(request, f"CSV文件 '{csv_file.name}' 导入完成，但存在 {len(errors)} 个错误。请查看详情。")
            for error in errors:
                messages.error(request, error)

        return render(request, 'management/import_csv.html', {'errors': errors, 'updated_count': updated_count, 'created_count': created_count})
    return render(request, 'management/import_csv.html')




@login_required
@user_passes_test(is_admin)
def sync_files(request):
    """
    同步media文件夹中的dwg、step和bmp文件到数据库
    """
    import os
    import re
    from django.conf import settings
    
    media_dir = os.path.join(settings.BASE_DIR, 'media')
    if not os.path.exists(media_dir):
        messages.error(request, "Media文件夹不存在")
        return redirect('clamps:management_dashboard')
    
    # 获取所有文件
    files = []
    for filename in os.listdir(media_dir):
        if filename.lower().endswith(('.dwg', '.step', '.bmp')):
            files.append(filename)
    
    updated_count = 0
    errors = []
    
    for filename in files:
        # 从文件名中提取图号
        # 假设文件名格式为: 图号.扩展名
        base_name = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1].lower()
        
        # 尝试匹配产品
        try:
            # 首先尝试精确匹配
            product = Product.objects.filter(drawing_no_1=base_name).first()
            
            if not product:
                # 如果精确匹配失败，尝试模糊匹配
                product = Product.objects.filter(drawing_no_1__icontains=base_name).first()
            
            if product:
                # 修改此处：不再加 media 前缀，因为我们已经在 media 目录下
                file_path = filename  # ✅ 关键修改点

                # 根据文件扩展名更新对应字段
                if extension == '.dwg':
                    product.dwg_file_path = file_path
                elif extension == '.step':
                    product.step_file_path = file_path
                elif extension == '.bmp':
                    product.bmp_file_path = file_path
                
                product.save()
                updated_count += 1
            else:
                errors.append(f"未找到匹配的产品: {base_name}")
                
        except Exception as e:
            errors.append(f"处理文件 {filename} 时发生错误: {e}")
    
    # 记录日志
    log_entry = Log(user=request.user, action_type='sync_files', ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details=f'Synced files. Updated: {updated_count}, Errors: {len(errors)}.')
    log_entry.save()
    
    if not errors:
        messages.success(request, f"文件同步成功！更新了 {updated_count} 个产品的文件路径。")
    else:
        messages.warning(request, f"文件同步完成，更新了 {updated_count} 个产品，但存在 {len(errors)} 个错误。")
        for error in errors:
            messages.error(request, error)
    
    return redirect('clamps:management_dashboard')



@login_required
def batch_download(request, file_type):
    """批量下载文件"""
    import zipfile
    import tempfile
    
    product_ids = request.GET.get('ids', '').split(',')
    if not product_ids or product_ids == ['']:
        messages.error(request, '未选择任何产品进行下载。')
        return redirect('clamps:search_results')
    
    # 获取选中的产品
    products = Product.objects.filter(id__in=product_ids)
    
    if not products.exists():
        messages.error(request, '未找到选中的产品。')
        return redirect('clamps:search_results')
    
    # 创建临时ZIP文件
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            file_count = 0
            
            for product in products:
                # 根据文件类型获取对应的文件路径
                file_paths = []
                
                if file_type == 'dwg':
                    if product.dwg_file_path:
                        file_paths.append(('dwg', product.dwg_file_path))
                elif file_type == 'step':
                    if product.step_file_path:
                        file_paths.append(('step', product.step_file_path))
                elif file_type == 'both':
                    if product.dwg_file_path:
                        file_paths.append(('dwg', product.dwg_file_path))
                    if product.step_file_path:
                        file_paths.append(('step', product.step_file_path))
                
                for file_ext, file_path in file_paths:
                    # 确保文件路径是相对于 MEDIA_ROOT 的路径
                    if file_path.startswith('media/'):
                        file_path = file_path[len('media/'):]
                    elif file_path.startswith('/media/'):
                        file_path = file_path[len('/media/'):]
                    
                    full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
                    
                    if os.path.exists(full_file_path):
                        # 生成ZIP内的文件名，包含产品描述或图号
                        product_name = product.drawing_no_1 or product.description or f"product_{product.id}"
                        # 清理文件名中的特殊字符
                        import re
                        product_name = re.sub(r'[<>:"/\\|?*]', '_', product_name)
                        
                        file_extension = os.path.splitext(file_path)[1]
                        zip_filename = f"{product_name}{file_extension}"
                        
                        # 如果文件名重复，添加序号
                        counter = 1
                        original_zip_filename = zip_filename
                        while zip_filename in [info.filename for info in zip_file.infolist()]:
                            name_without_ext = os.path.splitext(original_zip_filename)[0]
                            zip_filename = f"{name_without_ext}_{counter}{file_extension}"
                            counter += 1
                        
                        zip_file.write(full_file_path, zip_filename)
                        file_count += 1
            
            if file_count == 0:
                file_type_display = {
                    'dwg': 'DWG',
                    'step': 'STEP',
                    'both': 'DWG或STEP'
                }.get(file_type, file_type.upper())
                messages.error(request, f'所选产品中没有可用的 {file_type_display} 文件。')
                return redirect('clamps:search_results')
        
        # 读取ZIP文件内容并返回
        with open(temp_zip.name, 'rb') as zip_file:
            response = HttpResponse(zip_file.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="batch_download_{file_type}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip"'
            
            # 记录批量下载日志
            log_entry = Log(
                user=request.user, 
                action_type='batch_download', 
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''), 
                details=f'Batch downloaded {file_count} {file_type} files for products: {", ".join(product_ids)}'
            )
            log_entry.save()
            
            return response
            
    except Exception as e:
        messages.error(request, f'批量下载时发生错误: {str(e)}')
        return redirect('clamps:search_results')
    
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_zip.name)
        except:
            pass

