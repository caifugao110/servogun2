from django.urls import path, include, re_path
from . import views

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
    path('logout_en/', views.user_logout_en, name='logout_en'), # 新增：专门用于英文登出的URL
    path("search_en/", views.search_en, name="search_en"),
    path('search/results_en/', views.search_results_en, name='search_results_en'),
    re_path(r'^product/(?P<product_id>\d+)_en/$', views.product_detail_en, name='product_detail_en'),

    # 管理功能 (保持不变)
    path('management/', views.management_dashboard, name='management_dashboard'),
    path('management/users/', views.manage_users, name='manage_users'),
    path('management/users/toggle/<int:user_id>/', views.toggle_user_active, name='toggle_user_active'),
    path('management/users/reset_password/<int:user_id>/', views.reset_user_password, name='reset_user_password'),
    path("management/users/delete/<int:user_id>/", views.delete_user, name="delete_user"),
    path("management/users/add/", views.add_user, name="add_user"),
    path("management/users/export/", views.export_users, name="export_users"),
    path('management/logs/', views.view_logs, name='view_logs'),
    path('management/export/', views.export_data, name='export_data'),
    path('management/import_csv/', views.import_csv, name='import_csv'),
    path('management/sync_files/', views.sync_files, name='sync_files'),
    
    # Gitee API代理
    path('api/gitee/releases/latest/<str:owner>/<str:repo>/', views.gitee_releases_latest, name='gitee_releases_latest'),
]


