# 小原焊钳选型数据库系统

## 项目简介

小原焊钳选型数据库系统是一个专为小原（南京）机电有限公司开发的在线焊钳产品选型平台。系统基于Django框架构建，提供高效、准确的焊钳产品查询和选型服务。

## 主要功能

- **产品搜索**：支持多条件组合搜索，快速定位符合要求的焊钳产品
- **产品详情**：查看详细的技术参数和产品信息
- **文件下载**：下载DWG、STEP、BMP等技术文档
- **用户管理**：完整的用户认证和权限管理系统
- **管理后台**：数据管理、日志查看、用户管理等管理功能
- **响应式设计**：支持桌面和移动设备访问

## 技术栈

- **后端**：Python 3.11 + Django 5.2.3
- **数据库**：SQLite（默认）/ PostgreSQL（生产环境）
- **前端**：HTML5 + CSS3 + Bootstrap 5 + JavaScript
- **图标**：Bootstrap Icons

## 快速开始

### 环境要求

- Python 3.11+
- pip 21.0+

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd welding_clamp_project
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # 或
   venv\Scripts\activate     # Windows
   ```

3. **安装依赖**
   ```bash
   pip install django==5.2.3
   pip install pillow
   pip install chardet
   ```
   
4. **数据库初始化**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py init_data
   ```

5. **创建管理员账户**
   ```bash
   python manage.py createsuperuser
   ```

6. **启动服务器**
   
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   
7. **访问系统**
   - 前台：http://localhost:8000
   - 管理后台：http://localhost:8000/admin

## 默认账户

系统初始化后会创建以下测试账户：

- **管理员账户**：admin / admin123
- **普通用户**：testuser / test123

## 项目结构

```
welding_clamp_project/
├── manage.py                    # Django管理脚本
├── welding_clamp_db/           # 项目配置
│   ├── settings.py             # 项目设置
│   ├── urls.py                 # URL路由
│   └── wsgi.py                 # WSGI配置
├── clamps/                     # 主应用
│   ├── models.py               # 数据模型
│   ├── views.py                # 视图函数
│   ├── urls.py                 # 应用URL
│   ├── admin.py                # 管理后台
│   └── middleware.py           # 中间件
├── templates/                  # 模板文件
├── static/                     # 静态文件
├── media/                      # 媒体文件
└── 系统使用文档.md              # 详细文档
```

## 数据库设计

### 主要模型

- **Category**：产品分类模型
- **Product**：产品信息模型
- **Log**：操作日志模型

### 分类结构

- **一级分类**：X2C、X2C-V2、X2C-V3
- **二级分类**：{一级分类}-C、{一级分类}-X

## 部署说明

### 开发环境

使用Django内置开发服务器，适合开发和测试。

### 生产环境

推荐使用以下配置：
- **Web服务器**：Nginx + Gunicorn
- **数据库**：PostgreSQL
- **操作系统**：Ubuntu 22.04 LTS

详细部署步骤请参考《系统使用文档.md》。

## 文件管理

### 文件类型

- **DWG文件**：AutoCAD图纸文件
- **STEP文件**：三维模型文件
- **BMP文件**：产品预览图片

### 文件存储

```
media/
├── products/
│   ├── dwg/          # DWG文件
│   ├── step/         # STEP文件
│   └── bmp/          # BMP图片
```

### 文件命名

文件按照图号命名：`{图号1(o)}.{扩展名}`

## 安全特性

- **用户认证**：Django内置认证系统
- **权限控制**：基于角色的访问控制
- **密码加密**：PBKDF2算法加密
- **CSRF保护**：防止跨站请求伪造
- **操作日志**：记录所有用户操作

## 管理功能

- **用户管理**：创建、修改、删除用户账户
- **数据管理**：产品信息和分类管理
- **日志管理**：查看和分析操作日志
- **数据导出**：导出产品数据和日志
- **系统监控**：查看系统统计信息

## 常见问题

### 1. 如何添加新产品？

通过Django管理后台（/admin）添加新产品信息。

### 2. 如何上传产品文件？

将文件按照命名规范上传到对应的media目录。

### 3. 如何重置用户密码？

管理员可以通过用户管理界面重置密码。

### 4. 如何备份数据？

```bash
# 导出数据
python manage.py dumpdata > backup.json

# 备份媒体文件
tar -czf media_backup.tar.gz media/
```

## 技术支持

如有问题请联系：
- **邮箱**：support@obara-nanjing.com
- **电话**：+86-25-XXXXXXXX

## 许可证

版权归小原（南京）机电有限公司所有。

## 更新日志

### v1.0.0 (2025-06-14)
- 初始版本发布
- 实现基础搜索功能
- 完成用户管理系统
- 添加文件下载功能
- 实现管理后台

