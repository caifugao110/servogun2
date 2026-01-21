# 小原焊枪选型数据库 - 部署文档

## 1. 环境准备

### 1.1 系统要求
- Windows Server 2016 或更高版本
- Python 3.9 或更高版本
- 至少 4GB 内存
- 至少 50GB 磁盘空间

### 1.2 软件安装
1. 安装 Python 3.9+（推荐使用 Python 3.11）
2. 安装 Git（可选，用于版本控制）
3. 安装 IIS（用于反向代理）

## 2. 项目部署

### 2.1 克隆或复制项目
将项目文件复制到服务器上的目标目录，例如 `D:\MyTrae\servogun2`。

### 2.2 创建虚拟环境
在项目根目录下创建虚拟环境：

```bash
cd /d "T:\Servo Gun\release"
```

```bash
python -m venv venv
```

### 2.3 激活虚拟环境

```bash
venv\Scripts\activate
```

### 2.4 安装依赖

```bash
pip install -r requirements.txt
```

### 2.5 配置环境变量
编辑项目根目录下的 `.env` 文件，根据实际情况修改配置：

```env
# Django settings
DEBUG=False
SECRET_KEY=django-insecure-your-secret-key-here-change-in-production

# Database settings
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
# DB_USER=your_db_user
# DB_PASSWORD=your_db_password
# DB_HOST=your_db_host
# DB_PORT=your_db_port

# Allowed hosts
ALLOWED_HOSTS=*

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS=http://gun.obara.com.cn

# Channel layer settings (optional, use redis for production)
# CHANNEL_LAYER_BACKEND=redis
# REDIS_URL=redis://localhost:6379/0
```

### 2.6 收集静态文件

```bash
python manage.py collectstatic --noinput
```

### 2.7 数据库迁移

```bash
python manage.py migrate
```

### 2.8 创建超级用户（可选）

```bash
python manage.py createsuperuser
```

## 3. 服务安装与管理

### 3.1 安装为 Windows 服务
使用项目提供的 `install_service.py` 脚本将应用安装为 Windows 服务：

1. 以管理员身份运行命令提示符
2. 激活虚拟环境
3. 执行以下命令：

```bash
python initial_setup/deployment_scripts/install_service.py
```

### 3.2 服务管理

#### 启动服务
```bash
python initial_setup/deployment_scripts/install_service.py --start
```

#### 停止服务
```bash
python initial_setup/deployment_scripts/install_service.py --stop
```

#### 卸载服务
```bash
python initial_setup/deployment_scripts/install_service.py --uninstall
```

### 3.3 手动启动服务
如果不需要安装为 Windows 服务，可以使用以下命令手动启动：

```bash
python initial_setup/deployment_scripts/start_wsgi.py
```

或使用批处理文件：

```bash
initial_setup/deployment_scripts/start_production.bat
```

## 4. IIS 反向代理配置

### 4.1 安装 IIS 角色和功能
1. 打开「服务器管理器」
2. 点击「添加角色和功能」
3. 选择「Web 服务器 (IIS)」
4. 确保安装以下角色服务：
   - Web 服务器
     - 常用 HTTP 功能
       - 静态内容
       - 默认文档
       - 目录浏览
       - HTTP 错误
     - 应用程序开发
       - .NET 扩展性
       - ASP.NET
     - 健康和诊断
       - HTTP 日志记录
     - 安全性
       - 请求筛选
       - Windows 身份验证
     - 性能
       - 静态内容压缩
       - 动态内容压缩
     - 管理工具
       - IIS 管理控制台

### 4.2 安装 URL 重写模块
从 [Microsoft 官方网站](https://www.iis.net/downloads/microsoft/url-rewrite) 下载并安装 URL 重写模块 2.1。

### 4.3 安装应用请求路由 (ARR)
从 [Microsoft 官方网站](https://www.iis.net/downloads/microsoft/application-request-routing) 下载并安装应用请求路由 3.0。

### 4.4 配置反向代理
1. 打开「IIS 管理器」
2. 选择服务器节点，双击「应用请求路由缓存」
3. 在右侧操作面板中点击「服务器代理设置」
4. 勾选「启用代理」，点击「应用」
5. 回到 IIS 管理器，选择网站节点，双击「URL 重写」
6. 点击右侧操作面板中的「添加规则...」
7. 选择「反向代理」，点击「确定」
8. 在「入站规则」中配置：
   - 传入 URL 模式：`(.*)`
   - 重写 URL：`http://localhost:6931/{R:1}`
   - 勾选「启用 SSL 终止」（如果使用 HTTPS）
9. 点击「应用」保存配置

### 4.5 配置网站绑定
1. 选择网站节点，点击右侧操作面板中的「绑定...」
2. 点击「添加...」
3. 配置：
   - 类型：`http`
   - IP 地址：`*` 或特定 IP
   - 端口：`80`
   - 主机名：`gun.obara.com.cn`
4. 点击「确定」保存配置

## 5. 监控与维护

### 5.1 日志文件
项目日志文件位于 `logs` 目录下：
- `django.log`：Django 应用日志
- `wsgi_server.log`：WSGI 服务器日志
- `service.log`：Windows 服务日志
- `service_error.log`：Windows 服务错误日志

### 5.2 定期备份
1. 定期备份数据库文件（`db.sqlite3` 或其他数据库）
2. 定期备份静态文件和媒体文件
3. 定期备份配置文件

### 5.3 性能优化
1. 启用 DEBUG=False（已在生产环境配置中设置）
2. 使用缓存系统（如 Redis）
3. 优化数据库查询
4. 启用静态文件压缩
5. 配置适当的连接超时和线程数

## 6. 常见问题与解决方案

### 6.1 服务启动失败
- 检查日志文件 `service_error.log` 获取详细错误信息
- 确保虚拟环境存在且依赖已正确安装
- 确保端口 6931 未被占用

### 6.2 外网无法访问
- 检查 IIS 反向代理配置是否正确
- 检查服务器防火墙是否允许端口 80 和 6931 的访问
- 检查域名解析是否正确

### 6.3 数据库连接失败
- 检查 `.env` 文件中的数据库配置是否正确
- 确保数据库服务正在运行
- 确保数据库用户具有正确的权限

### 6.4 静态文件无法访问
- 确保已执行 `collectstatic` 命令
- 检查 IIS 静态文件配置是否正确
- 检查静态文件路径权限是否正确

## 7. 升级与更新

### 7.1 更新项目代码
1. 停止服务
2. 更新项目代码
3. 激活虚拟环境
4. 安装新的依赖
5. 执行数据库迁移
6. 收集静态文件
7. 启动服务

### 7.2 升级 Python 版本
1. 安装新版本 Python
2. 创建新的虚拟环境
3. 安装依赖
4. 测试应用
5. 更新服务配置

## 8. 安全建议

1. 定期更新依赖包
2. 使用强密码
3. 配置 HTTPS（推荐）
4. 限制服务器访问 IP
5. 定期检查日志文件
6. 配置适当的文件权限
7. 使用 WAF（Web 应用防火墙）保护

## 9. 联系方式

如有任何问题或建议，请联系技术支持团队。
