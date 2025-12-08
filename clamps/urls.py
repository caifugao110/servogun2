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

from django.urls import path, re_path
from . import views, media_views

app_name = 'clamps'

urlpatterns = [
    # 中文页面URL
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('search/', views.search, name='search'),
    path('search/results/', views.search_results, name='search_results'),
    re_path(r'^product/(?P<product_id>\d+)/$', views.product_detail, name='product_detail'),
    re_path(r'^download/(?P<product_id>\d+)/(?P<file_type>\w+)/$', views.download_file, name='download_file'),
    path('batch_download/<str:file_type>/', views.batch_download_view, name='batch_download'),
    re_path(r'^check_file_size/(?P<product_id>\d+)/(?P<file_type>\w+)/$', views.check_file_size, name='check_file_size'),
    path('check_batch_file_size/', views.check_batch_file_size, name='check_batch_file_size'),

    # 英文页面URL
    path('_en/', views.home_en, name='home_en'),
    path('login_en/', views.user_login_en, name='login_en'),
    path('logout_en/', views.user_logout_en, name='logout_en'),
    path('search_en/', views.search_en, name='search_en'),
    path('search/results_en/', views.search_results_en, name='search_results_en'),
    re_path(r'^product/(?P<product_id>\d+)_en/$', views.product_detail_en, name='product_detail_en'),

    # 管理功能
    path('management/', views.management_dashboard, name='management_dashboard'),
    path('management/users/', views.manage_users, name='manage_users'),
    path('management/users/toggle/<int:user_id>/', views.toggle_user_active, name='toggle_user_active'),
    path('management/users/reset_password/<int:user_id>/', views.reset_user_password, name='reset_user_password'),
    path('management/users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('management/users/add/', views.add_user, name='add_user'),
    path('management/users/export/', views.export_users, name='export_users'),
    path('management/logs/', views.view_logs, name='view_logs'),
    path('management/export/', views.export_data, name='export_data'),
    path('management/import_csv/', views.import_csv, name='import_csv'),
    path('management/sync_files/', views.sync_files, name='sync_files'),
    path('management/analytics/', views.analytics_view, name='analytics'),
    path('management/user_feedback/', views.manage_user_feedback, name='manage_user_feedback'),
    path('management/user_feedback/update_status/<int:feedback_id>/', views.update_feedback_status, name='update_feedback_status'),
    path('management/user_feedback/export/', views.export_user_feedback, name='export_user_feedback'),
    # 仕样管理
    path('management/style_links/create/', views.create_style_link, name='create_style_link'),
    path('management/style_links/my/', views.my_style_links, name='my_style_links'),
    path('management/style_links/edit/<int:link_id>/', views.edit_style_link, name='edit_style_link'),
    path('style-search/<str:unique_id>_en/', views.style_search_en, name='style_search_en'),
    path('style-search/<str:unique_id>/', views.style_search, name='style_search'),
    re_path(r'^style-search/*/?$', views.empty_style_search, name='empty_style_search'),
    re_path(r'^style-search_en/*/?$', views.empty_style_search_en, name='empty_style_search_en'),
    
    # 用户反馈
    path('feedback/', views.user_feedback, name='user_feedback'),
    path('feedback_en/', views.user_feedback_en, name='user_feedback_en'),
    
    # 个人中心
    path('profile/', views.profile, name='profile'),
    path('profile_en/', views.profile_en, name='profile_en'),
    
    # API接口
    path('api/gitee/releases/latest/<str:owner>/<str:repo>/', views.gitee_releases_latest, name='gitee_releases_latest'),
    path('api/download-analytics/', views.download_analytics_api, name='download_analytics_api'),
    path('api/ai_search/', views.ai_search_api, name='ai_search_api'),
    path('api/user_profile_data/', views.get_user_profile_data, name='get_user_profile_data'),
    
    # 媒体文件保护
    re_path(r'^protected_media/(?P<path>.*)$', media_views.protected_media, name='protected_media'),
]



