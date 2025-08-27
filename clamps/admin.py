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



from django.contrib import admin
from .models import Category, Product, Log

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_category', 'created_at', 'updated_at')
    list_filter = ('parent_category', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('drawing_no_1', 'description', 'category', 'sub_category_type', 'throat_depth', 'throat_width', 'transformer', 'created_at')
    list_filter = ('category', 'sub_category_type', 'transformer', 'has_balance', 'created_at')
    search_fields = ('drawing_no_1', 'description', 'transformer')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('基本信息', {
            'fields': ('category', 'description', 'drawing_no_1', 'sub_category_type')
        }),
        ('技术参数', {
            'fields': ('stroke', 'electrode_arm_end', 'clamping_force', 'electrode_arm_type', 
                      'transformer', 'weight', 'transformer_placement', 'flange_pcd',
                      'throat_depth', 'throat_width', 'has_balance', 'water_circuit')
        }),
        ('托架和齿轮箱', {
            'fields': ('bracket_direction', 'bracket_angle', 'motor_manufacturer', 'bracket_count',
                      'gearbox_type', 'bracket_material', 'gearbox_stroke', 'tool_changer')
        }),
        ('偏心参数', {
            'fields': ('eccentricity', 'eccentricity_direction', 'eccentricity_to_center', 'guidance_method')
        }),
        ('X型分类专用参数', {
            'fields': ('static_arm_eccentricity', 'static_electrode_arm_end', 'moving_arm_eccentricity',
                      'moving_electrode_arm_end', 'pivot_to_drive_center_dist', 'static_arm_front_length',
                      'static_arm_front_height', 'moving_arm_front_length', 'moving_arm_front_height')
        }),
        ('其他参数', {
            'fields': ('grip_extension_length',)
        }),
        ('文件路径', {
            'fields': ('dwg_file_path', 'step_file_path', 'bmp_file_path')
        }),
    )

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action_type', 'ip_address', 'path', 'method')
    list_filter = ('action_type', 'timestamp', 'method')
    search_fields = ('user__username', 'action_type', 'details', 'ip_address')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp',)
    
    def has_add_permission(self, request):
        return False  # 不允许手动添加日志
    
    def has_change_permission(self, request, obj=None):
        return False  # 不允许修改日志

