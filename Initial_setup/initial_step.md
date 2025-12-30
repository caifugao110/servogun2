# 小原焊枪选型数据库项目初始设置步骤

## 1. 克隆项目仓库

将项目从 Gitee 仓库克隆到本地计算机。

### 1.1 克隆命令

```bash
git clone https://gitee.com/caifugao110/servogun2.git
```

### 1.2 进入项目目录

```bash
cd servogun2
```

### 1.3 创建必要目录

根据 `.gitignore` 文件的配置，创建以下目录：

#### Windows 系统

在命令提示符（cmd.exe）中运行：
```cmd
if not exist media mkdir media & if not exist logs mkdir logs & if not exist backups mkdir backups
```

在 PowerShell 中运行：
```powershell
mkdir -Force media logs backups
```

#### Linux/macOS 系统

```bash
mkdir -p media logs backups  # 如果目录已存在则自动跳过
```

## 2. 安装依赖

确保您的系统已安装 Python 3.11 或更高版本，然后安装项目所需的所有依赖。

### 2.1 创建虚拟环境（可选但推荐）

#### Windows 系统
```bash
python -m venv venv
venv\Scripts\activate
```

#### Linux/macOS 系统
```bash
python -m venv venv
source venv/bin/activate
```

### 2.2 安装依赖包

```bash
pip install -r requirements.txt
```

## 3. 数据库迁移

运行数据库迁移命令，创建或更新数据库表结构。

```bash
python manage.py migrate
```

## 4. 收集静态文件

收集所有静态文件到staticfiles文件夹，用于生产环境部署：

```bash
python manage.py collectstatic --noinput
```

- `--noinput` 参数用于跳过确认提示，直接执行收集操作
- 该命令会将项目中的所有静态资源复制到 `staticfiles` 文件夹
- 生产环境会从该文件夹读取静态资源

## 5. 初始化分类数据（可选）

对于全新部署，可以运行以下命令初始化产品分类：

```bash
python manage.py init_data
```

## 6. 创建超级用户

创建一个管理员账户，用于登录系统和管理后台。

```bash
python manage.py createsuperuser
```

按照提示输入：
- 用户名（例如：admin）
- 邮箱（可选）
- 密码（至少 8 个字符，确保安全性）
- 确认密码

## 6. 获取Media文件（PDF, STEP, BMP）

### 6.1 概述

系统需要三种格式的媒体文件：
- **PDF**: 产品说明书
- **STEP**: 3D模型文件
- **BMP**: 产品图片

### 6.2 获取方式

#### 6.2.1 STEP文件获取

1. 从PDM系统导出原始数据
2. 提取图号并使用myprint工具下载DWG文件
3. 整理文件结构，生成DWG清单
4. 使用`copy_step_by_status.py`脚本从指定目录复制STEP文件：
   ```bash
   cd initial_setup/howtogetstep
   python copy_step_by_status.py
   ```
5. 将生成的STEP文件复制到项目的`media`目录

#### 6.2.2 BMP文件获取

1. 确保已获取STEP文件
2. 使用AUTOVUE软件批量转换STEP为BMP：
   - 启动AUTOVUE并打开任意DWG文件
   - 点击菜单栏：**文件 → 转换 → 批量转换**
   - 添加需要转换的STEP文件
   - 设置输出路径为项目的`media`目录
   - 选择目标格式为"Windows Bitmap" (.bmp)
   - 点击确定开始批量转换

#### 6.2.3 PDF文件获取

1. 从PDM系统或其他渠道获取PDF文件
2. 使用`rename_pdf_files.py`脚本处理PDF文件名中的逗号：
   ```bash
   cd initial_setup/howtogetpdf
   python rename_pdf_files.py
   ```
3. 使用`delete_r_ending_files.py`脚本删除以R结尾的文件：
   ```bash
   python delete_r_ending_files.py ../../media
   ```
4. 将处理后的PDF文件复制到项目的`media`目录

### 6.3 标准化流程

详细的获取media文件标准化流程请参考：`initial_setup/doc/获取media文件标准化流程.md`

## 7. 启动开发服务器

启动 Django 开发服务器，用于本地测试和开发。

### 7.1 默认端口启动

```bash
python manage.py runserver
```

系统默认运行在 `http://127.0.0.1:8000/`

### 7.2 指定端口启动（推荐使用 6931）

```bash
python manage.py runserver 0.0.0.0:6931
```

系统将运行在 `http://127.0.0.1:6931/` 或 `http://您的IP地址:6931/`

## 8. 访问系统

### 8.1 系统首页

在浏览器中访问：`http://127.0.0.1:6931/`

### 8.2 登录页面

访问：`http://127.0.0.1:6931/login/`

使用步骤 5 创建的超级用户账户登录系统。

### 8.3 管理后台

访问：`http://127.0.0.1:6931/admin/`

同样使用超级用户账户登录，可直接管理数据库中的数据。

## 9. 导入产品数据

### 9.1 预处理CSV文件

在导入之前，需要使用`process_csv.py`工具对从PDM导出来的CSV文件进行标准化处理：

```bash
cd initial_setup/csv
python process_csv.py
```

该脚本将：
- 自动识别文件编码
- 处理表头，统一列名
- 按标准表头顺序排序
- 处理图号1(o)列，删除以R结尾的行
- 删除"(利旧)"字符串和"/"字符
- 只保留图号非空的行

### 9.2 导入CSV文件

1. 登录系统
2. 导航到“管理仪表盘” -> “导入CSV” 或直接访问：`http://127.0.0.1:6931/management/import_csv/`
3. 选择预处理后的CSV文件（位于 `initial_setup/csv/` 目录下）
4. 点击“上传并导入”按钮
5. 查看导入结果（新增数量、更新数量和错误信息）

## 10. 文件同步

导入CSV文件完成后，需要将media文件夹中的文件与数据库中的产品记录进行同步：

1. 确保已将STEP、PDF、BMP文件放置在系统的`media`目录下
2. 登录系统
3. 导航到“管理仪表盘” -> “文件同步” 或直接访问：`http://127.0.0.1:6931/management/sync_files/`
4. 点击“同步文件”按钮
5. 在确认对话框中点击“确认同步”
6. 查看同步结果

### 10.1 查看未匹配文件

同步完成后，可以查看未匹配的文件：

1. 导航到“管理仪表盘” -> “查看未匹配文件” 或直接访问：`http://127.0.0.1:6931/management/unmatched_files/`
2. 查看未匹配的文件列表
3. 根据需要调整文件名或数据库记录，然后重新同步

## 11. 后续配置步骤

### 11.1 系统功能验证

1. **产品搜索**：
   - 登录系统
   - 进入搜索页面：`http://127.0.0.1:6931/search/`
   - 填写搜索条件
   - 点击“搜索”按钮查看结果

2. **产品详情与文件下载**：
   - 在搜索结果页面点击任一产品
   - 查看产品详情
   - 点击下载链接下载相关文件

3. **批量下载**：
   - 在搜索结果页面勾选多个产品
   - 点击“批量下载STEP”按钮
   - 下载生成的 ZIP 文件

### 11.2 管理功能

1. **用户管理**：
   - 访问：`http://127.0.0.1:6931/management/users/`
   - 查看用户列表
   - 启用/禁用用户
   - 重置用户密码
   - 删除用户

2. **数据导出**：
   - 访问：`http://127.0.0.1:6931/management/export/`
   - 导出产品数据
   - 导出用户数据
   - 导出日志数据

3. **系统日志**：
   - 访问：`http://127.0.0.1:6931/management/logs/`
   - 查看系统操作日志
   - 按操作类型、用户名、日期范围筛选

## 12. 开发与调试

### 12.1 查看运行日志

开发服务器启动后，控制台会显示实时运行日志，包括：
- 请求信息
- 错误信息
- 调试信息

### 12.2 代码修改

修改代码后，Django 开发服务器会自动重启，无需手动重启。

## 13. 注意事项

1. **Python 版本**：确保使用 Python 3.11 或更高版本
2. **虚拟环境**：推荐使用虚拟环境隔离项目依赖
3. **数据库备份**：定期备份数据库文件 `db.sqlite3`
4. **文件管理**：确保 `media` 目录下的文件与数据库中的产品记录保持同步
5. **安全设置**：在生产环境部署时，需配置适当的安全设置，如 SECRET_KEY、ALLOWED_HOSTS 等

## 14. 常见问题排查

### 14.1 端口被占用

如果提示端口被占用，可以使用其他端口启动服务器：

```bash
python manage.py runserver 0.0.0.0:8001
```

### 14.2 依赖安装失败

尝试升级 pip 后重新安装：

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 14.3 数据库迁移失败

检查数据库文件权限，确保当前用户有读写权限。

### 14.4 无法访问管理后台

确保已创建超级用户，并且使用正确的用户名和密码登录。

## 15. 联系方式

如有任何问题或建议，请通过以下方式联系：

- 邮箱：gaoj@obara.com.cn

---

**文档更新日期**：2025-12-13
**项目版本**：最新版本
**作者**：技术开发二部