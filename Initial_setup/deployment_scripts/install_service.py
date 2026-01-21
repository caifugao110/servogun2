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

"""
Windows服务安装脚本，使用NSSM（Non-Sucking Service Manager）
用于将Django应用注册为Windows服务，实现自动启动和后台运行
"""

import os
import sys
import subprocess
import logging
import shutil
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/service_install.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 项目根目录（上两级目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 检测E盘是否存在，选择NSSM基础目录
if Path("E:/").exists():
    NSSM_BASE_DIR = Path("E:/Servogun Server")
else:
    NSSM_BASE_DIR = Path("D:/Servogun Server")

# 确保NSSM基础目录存在
os.makedirs(NSSM_BASE_DIR, exist_ok=True)

# NSSM下载链接
NSSM_URL = "https://nssm.cc/release/nssm-2.24.zip"
NSSM_ZIP = NSSM_BASE_DIR / "nssm-2.24.zip"
NSSM_DIR = NSSM_BASE_DIR / "nssm-2.24"
NSSM_EXE = NSSM_DIR / "win64" / "nssm.exe"  # 使用64位版本

# 服务配置
SERVICE_NAME = "DjangoServogun"
SERVICE_DISPLAY_NAME = "Django Servogun Server"
SERVICE_DESCRIPTION = "小原焊枪选型数据库Django服务"

# Python可执行文件路径（虚拟环境）
PYTHON_EXE = BASE_DIR / "venv" / "Scripts" / "python.exe"

# 启动脚本路径
START_SCRIPT = BASE_DIR / "initial_setup" / "deployment_scripts" / "start_wsgi.py"

# 日志路径
LOG_DIR = BASE_DIR / "logs"
SERVICE_LOG_FILE = LOG_DIR / "service.log"
SERVICE_ERROR_LOG_FILE = LOG_DIR / "service_error.log"


def download_nssm():
    """下载NSSM工具"""
    import requests
    from zipfile import ZipFile, BadZipFile
    
    logger.info(f"正在下载NSSM工具: {NSSM_URL}")
    
    # 下载NSSM压缩包
    try:
        response = requests.get(NSSM_URL, timeout=30)
        # 检查响应状态码
        response.raise_for_status()
        
        # 检查内容类型
        if 'application/zip' not in response.headers.get('Content-Type', ''):
            logger.error(f"下载的文件不是有效的ZIP文件，Content-Type: {response.headers.get('Content-Type')}")
            logger.error("可能是NSSM服务器暂时不可用（503错误）")
            
            # 检查是否已经存在NSSM可执行文件
            if NSSM_EXE.exists():
                logger.info(f"使用已存在的NSSM可执行文件: {NSSM_EXE}")
                return
            else:
                logger.error(f"请手动下载NSSM工具并解压到 {NSSM_DIR} 目录")
                logger.error("NSSM下载地址: https://nssm.cc/release/nssm-2.24.zip")
                sys.exit(1)
        
        with open(NSSM_ZIP, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"NSSM下载完成，保存到: {NSSM_ZIP}")
    except requests.exceptions.RequestException as e:
        logger.error(f"下载NSSM工具失败: {e}")
        logger.error("可能是NSSM服务器暂时不可用（503错误）")
        
        # 检查是否已经存在NSSM可执行文件
        if NSSM_EXE.exists():
            logger.info(f"使用已存在的NSSM可执行文件: {NSSM_EXE}")
            return
        else:
            logger.error(f"请手动下载NSSM工具并解压到 {NSSM_DIR} 目录")
            logger.error("NSSM下载地址: https://nssm.cc/release/nssm-2.24.zip")
            sys.exit(1)
    
    # 确保解压目录存在
    os.makedirs(NSSM_DIR, exist_ok=True)
    
    # 解压NSSM到指定目录
    logger.info(f"正在解压NSSM到: {NSSM_DIR}")
    try:
        with ZipFile(NSSM_ZIP, 'r') as zip_ref:
            # 获取压缩包中的所有成员
            for member in zip_ref.namelist():
                # 跳过空目录
                if member.endswith('/') or member.endswith('\\'):
                    continue
                
                # 移除压缩包中的根目录
                # 假设压缩包的结构是 nssm-2.24/xxx，我们需要提取 xxx 部分
                parts = member.split('/') if '/' in member else member.split('\\')
                
                # 跳过根目录，直接使用子目录和文件名
                if len(parts) > 1:
                    # 移除第一个元素（根目录）
                    target_filename = os.path.join(NSSM_DIR, *parts[1:])
                else:
                    # 直接使用文件名
                    target_filename = os.path.join(NSSM_DIR, member)
                
                # 创建目标目录
                os.makedirs(os.path.dirname(target_filename), exist_ok=True)
                
                # 解压文件
                with open(target_filename, 'wb') as f:
                    f.write(zip_ref.read(member))
        
        logger.info(f"NSSM解压完成")
        
        # 删除压缩包
        os.remove(NSSM_ZIP)
        logger.info(f"已删除NSSM压缩包")
        
        # 验证解压结果
        if not NSSM_EXE.exists():
            logger.error(f"NSSM可执行文件未找到: {NSSM_EXE}")
            logger.error("请手动检查解压目录结构")
            # 列出目录结构，方便调试
            logger.error("当前目录结构:")
            for root, dirs, files in os.walk(NSSM_DIR):
                level = root.replace(NSSM_DIR, '').count(os.sep)
                indent = ' ' * 2 * level
                logger.error(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    logger.error(f"{subindent}{file}")
            
            # 检查是否已经存在NSSM可执行文件
            if NSSM_EXE.exists():
                logger.info(f"使用已存在的NSSM可执行文件: {NSSM_EXE}")
                return
            else:
                logger.error(f"请手动下载NSSM工具并解压到 {NSSM_DIR} 目录")
                logger.error("NSSM下载地址: https://nssm.cc/release/nssm-2.24.zip")
                sys.exit(1)
        
        logger.info(f"NSSM可执行文件已找到: {NSSM_EXE}")
    except BadZipFile as e:
        logger.error(f"解压NSSM工具失败: {e}")
        logger.error("下载的文件可能已损坏")
        
        # 删除损坏的压缩包
        if os.path.exists(NSSM_ZIP):
            os.remove(NSSM_ZIP)
        
        # 检查是否已经存在NSSM可执行文件
        if NSSM_EXE.exists():
            logger.info(f"使用已存在的NSSM可执行文件: {NSSM_EXE}")
            return
        else:
            logger.error(f"请手动下载NSSM工具并解压到 {NSSM_DIR} 目录")
            logger.error("NSSM下载地址: https://nssm.cc/release/nssm-2.24.zip")
            sys.exit(1)


def install_nssm_service():
    """安装NSSM服务"""
    # 检查NSSM是否存在
    nssm_exe_candidates = [
        NSSM_EXE,  # 首选：指定的NSSM_DIR目录
    ]
    
    actual_nssm_exe = None
    for candidate in nssm_exe_candidates:
        if candidate.exists():
            actual_nssm_exe = candidate
            logger.info(f"使用NSSM可执行文件: {actual_nssm_exe}")
            break
    
    if actual_nssm_exe is None:
        # 如果没有找到NSSM可执行文件，尝试下载
        logger.info("未找到NSSM可执行文件，尝试下载...")
        download_nssm()
        # 再次检查
        if NSSM_EXE.exists():
            actual_nssm_exe = NSSM_EXE
        else:
            logger.error(f"NSSM可执行文件未找到: {NSSM_EXE}")
            logger.error("请手动检查NSSM安装")
            sys.exit(1)
    
    # 检查Python可执行文件是否存在
    if not PYTHON_EXE.exists():
        logger.error(f"Python可执行文件不存在: {PYTHON_EXE}")
        logger.error("请先创建并激活虚拟环境")
        sys.exit(1)
    
    # 检查启动脚本是否存在
    if not START_SCRIPT.exists():
        logger.error(f"启动脚本不存在: {START_SCRIPT}")
        sys.exit(1)
    
    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 检查服务是否已经存在，如果存在则先卸载
    logger.info(f"检查服务是否已经存在: {SERVICE_NAME}")
    check_cmd = [str(actual_nssm_exe), "status", SERVICE_NAME]
    try:
        subprocess.run(check_cmd, capture_output=True, text=False, check=True)
        logger.info(f"服务已经存在，尝试卸载: {SERVICE_NAME}")
        # 停止服务
        stop_cmd = [str(actual_nssm_exe), "stop", SERVICE_NAME]
        subprocess.run(stop_cmd, capture_output=True, text=False, check=False)
        # 卸载服务
        uninstall_cmd = [str(actual_nssm_exe), "remove", SERVICE_NAME, "confirm"]
        subprocess.run(uninstall_cmd, capture_output=True, text=False, check=False)
        logger.info(f"已卸载现有服务: {SERVICE_NAME}")
    except subprocess.CalledProcessError:
        # 服务不存在，继续安装
        logger.info(f"服务不存在，继续安装: {SERVICE_NAME}")
    
    logger.info(f"正在安装Windows服务: {SERVICE_NAME}")
    
    # 构建NSSM命令
    install_cmd = [str(actual_nssm_exe), "install", SERVICE_NAME, str(PYTHON_EXE), str(START_SCRIPT)]
    
    # 执行安装命令
    try:
        # 使用合适的编码处理输出，避免UnicodeDecodeError
        result = subprocess.run(install_cmd, capture_output=True, text=False, check=True)
        logger.info(f"执行命令成功: {' '.join(install_cmd)}")
        if result.stdout:
            try:
                # 尝试使用utf-8编码解码输出
                stdout_str = result.stdout.decode('utf-8', errors='replace').strip()
                # 过滤掉不可打印字符
                stdout_str = ''.join(c for c in stdout_str if c.isprintable() or c.isspace())
                # 移除多余的空格
                import re
                stdout_str = re.sub(r'\s+', ' ', stdout_str)
                # 进一步过滤掉无法被GBK编码的字符
                stdout_str = stdout_str.encode('gbk', errors='ignore').decode('gbk')
                if stdout_str:
                    logger.info(f"命令输出: {stdout_str}")
            except Exception:
                # 如果解码失败，忽略输出
                pass
    except subprocess.CalledProcessError as e:
        logger.error(f"执行安装命令失败: {' '.join(install_cmd)}")
        logger.error(f"命令返回码: {e.returncode}")
        if e.stdout:
            try:
                stdout_str = e.stdout.decode('utf-8', errors='ignore').strip()
                logger.error(f"标准输出: {stdout_str}")
            except:
                pass
        if e.stderr:
            try:
                stderr_str = e.stderr.decode('utf-8', errors='ignore').strip()
                logger.error(f"错误输出: {stderr_str}")
            except:
                pass
        logger.error("请手动检查命令执行情况")
        logger.error("可能的原因：")
        logger.error("1. 服务已存在，且无法卸载")
        logger.error("2. 没有足够的管理员权限")
        logger.error("3. Python可执行文件或启动脚本路径错误")
        sys.exit(1)
    
    # 设置服务参数
    service_params = [
        # 设置工作目录
        [str(actual_nssm_exe), "set", SERVICE_NAME, "AppDirectory", str(BASE_DIR)],
        # 设置显示名称
        [str(actual_nssm_exe), "set", SERVICE_NAME, "DisplayName", SERVICE_DISPLAY_NAME],
        # 设置描述
        [str(actual_nssm_exe), "set", SERVICE_NAME, "Description", SERVICE_DESCRIPTION],
        # 设置启动方式为自动
        [str(actual_nssm_exe), "set", SERVICE_NAME, "Start", "SERVICE_AUTO_START"],
        # 设置日志文件
        [str(actual_nssm_exe), "set", SERVICE_NAME, "AppStdout", str(SERVICE_LOG_FILE)],
        [str(actual_nssm_exe), "set", SERVICE_NAME, "AppStderr", str(SERVICE_ERROR_LOG_FILE)],
        [str(actual_nssm_exe), "set", SERVICE_NAME, "AppRotateFiles", "1"],  # 启用日志轮转
        [str(actual_nssm_exe), "set", SERVICE_NAME, "AppRotateBytes", "10485760"],  # 日志文件大小限制10MB
        [str(actual_nssm_exe), "set", SERVICE_NAME, "AppRotateSeconds", "86400"],  # 每天轮转一次
    ]
    
    # 执行服务参数设置命令
    for cmd in service_params:
        try:
            # 使用合适的编码处理输出，避免UnicodeDecodeError
            result = subprocess.run(cmd, capture_output=True, text=False, check=True)
            logger.info(f"执行命令成功: {' '.join(cmd)}")
            if result.stdout:
                try:
                    # 尝试使用utf-8编码解码输出
                    stdout_str = result.stdout.decode('utf-8', errors='replace').strip()
                    # 过滤掉不可打印字符
                    stdout_str = ''.join(c for c in stdout_str if c.isprintable() or c.isspace())
                    # 移除多余的空格
                    import re
                    stdout_str = re.sub(r'\s+', ' ', stdout_str)
                    # 进一步过滤掉无法被GBK编码的字符
                    stdout_str = stdout_str.encode('gbk', errors='ignore').decode('gbk')
                    if stdout_str:
                        logger.info(f"命令输出: {stdout_str}")
                except Exception:
                    # 如果解码失败，忽略输出
                    pass
        except subprocess.CalledProcessError as e:
            logger.error(f"执行命令失败: {' '.join(cmd)}")
            logger.error(f"命令返回码: {e.returncode}")
            if e.stdout:
                try:
                    stdout_str = e.stdout.decode('utf-8', errors='replace').strip()
                    # 过滤掉不可打印字符
                    stdout_str = ''.join(c for c in stdout_str if c.isprintable() or c.isspace())
                    # 移除多余的空格
                    import re
                    stdout_str = re.sub(r'\s+', ' ', stdout_str)
                    if stdout_str:
                        logger.error(f"标准输出: {stdout_str}")
                except:
                    pass
            if e.stderr:
                try:
                    stderr_str = e.stderr.decode('utf-8', errors='replace').strip()
                    # 过滤掉不可打印字符
                    stderr_str = ''.join(c for c in stderr_str if c.isprintable() or c.isspace())
                    # 移除多余的空格
                    import re
                    stderr_str = re.sub(r'\s+', ' ', stderr_str)
                    if stderr_str:
                        logger.error(f"错误输出: {stderr_str}")
                except:
                    pass
            logger.error("请手动检查命令执行情况")
            sys.exit(1)
    
    # 启动服务
    logger.info(f"正在启动服务: {SERVICE_NAME}")
    start_cmd = [str(actual_nssm_exe), "start", SERVICE_NAME]
    try:
        # 使用合适的编码处理输出，避免UnicodeDecodeError
        result = subprocess.run(start_cmd, capture_output=True, text=False, check=True)
        if result.stdout:
            try:
                # 尝试使用utf-8编码解码输出
                stdout_str = result.stdout.decode('utf-8', errors='replace').strip()
                # 过滤掉不可打印字符
                stdout_str = ''.join(c for c in stdout_str if c.isprintable() or c.isspace())
                # 移除多余的空格
                import re
                stdout_str = re.sub(r'\s+', ' ', stdout_str)
                # 进一步过滤掉无法被GBK编码的字符
                stdout_str = stdout_str.encode('gbk', errors='ignore').decode('gbk')
                if stdout_str:
                    logger.info(f"服务启动成功: {stdout_str}")
                else:
                    logger.info(f"服务启动成功")
            except Exception:
                # 如果解码失败，忽略输出
                logger.info(f"服务启动成功")
    except subprocess.CalledProcessError as e:
        logger.error(f"服务启动失败")
        logger.error(f"命令返回码: {e.returncode}")
        if e.stdout:
            try:
                stdout_str = e.stdout.decode('utf-8', errors='replace').strip()
                # 过滤掉不可打印字符
                stdout_str = ''.join(c for c in stdout_str if c.isprintable() or c.isspace())
                # 移除多余的空格
                import re
                stdout_str = re.sub(r'\s+', ' ', stdout_str)
                if stdout_str:
                    logger.error(f"标准输出: {stdout_str}")
            except:
                pass
        if e.stderr:
            try:
                stderr_str = e.stderr.decode('utf-8', errors='replace').strip()
                # 过滤掉不可打印字符
                stderr_str = ''.join(c for c in stderr_str if c.isprintable() or c.isspace())
                # 移除多余的空格
                import re
                stderr_str = re.sub(r'\s+', ' ', stderr_str)
                if stderr_str:
                    logger.error(f"错误输出: {stderr_str}")
            except:
                pass
        logger.error("请检查服务配置和日志文件")
        logger.error("您可以在Windows服务管理器中手动启动服务，并查看服务日志")
        sys.exit(1)
    
    logger.info(f"Windows服务安装完成: {SERVICE_NAME}")
    logger.info(f"服务显示名称: {SERVICE_DISPLAY_NAME}")
    logger.info(f"服务描述: {SERVICE_DESCRIPTION}")
    logger.info(f"服务日志文件: {SERVICE_LOG_FILE}")
    logger.info(f"服务错误日志文件: {SERVICE_ERROR_LOG_FILE}")
    logger.info("您可以在Windows服务管理器中查看和管理此服务")


def uninstall_nssm_service():
    """卸载NSSM服务"""
    # 检查NSSM是否存在
    nssm_exe_candidates = [
        NSSM_EXE,  # 首选：指定的NSSM_DIR目录
    ]
    
    actual_nssm_exe = None
    for candidate in nssm_exe_candidates:
        if candidate.exists():
            actual_nssm_exe = candidate
            logger.info(f"使用NSSM可执行文件: {actual_nssm_exe}")
            break
    
    if actual_nssm_exe is None:
        logger.error(f"NSSM可执行文件未找到")
        logger.error("请手动卸载服务")
        sys.exit(1)
    
    logger.info(f"正在停止服务: {SERVICE_NAME}")
    # 停止服务
    stop_cmd = [str(actual_nssm_exe), "stop", SERVICE_NAME]
    try:
        # 使用合适的编码处理输出，避免UnicodeDecodeError
        result = subprocess.run(stop_cmd, capture_output=True, text=False, check=True)
        logger.info(f"服务停止成功")
        if result.stdout:
            try:
                # 尝试使用utf-8编码解码输出
                stdout_str = result.stdout.decode('utf-8', errors='replace').strip()
                # 过滤掉不可打印字符
                stdout_str = ''.join(c for c in stdout_str if c.isprintable() or c.isspace())
                # 移除多余的空格
                import re
                stdout_str = re.sub(r'\s+', ' ', stdout_str)
                # 进一步过滤掉无法被GBK编码的字符
                stdout_str = stdout_str.encode('gbk', errors='ignore').decode('gbk')
                if stdout_str:
                    logger.info(f"命令输出: {stdout_str}")
            except Exception:
                # 如果解码失败，忽略输出
                pass
    except subprocess.CalledProcessError as e:
        logger.warning(f"服务停止失败（可能服务未运行）")
        if e.stderr:
            try:
                stderr_str = e.stderr.decode('utf-8', errors='replace').strip()
                # 过滤掉不可打印字符
                stderr_str = ''.join(c for c in stderr_str if c.isprintable() or c.isspace())
                # 移除多余的空格
                import re
                stderr_str = re.sub(r'\s+', ' ', stderr_str)
                if stderr_str:
                    logger.warning(f"错误输出: {stderr_str}")
            except:
                pass
    
    logger.info(f"正在卸载服务: {SERVICE_NAME}")
    # 卸载服务
    uninstall_cmd = [str(actual_nssm_exe), "remove", SERVICE_NAME, "confirm"]
    try:
        # 使用合适的编码处理输出，避免UnicodeDecodeError
        result = subprocess.run(uninstall_cmd, capture_output=True, text=False, check=True)
        logger.info(f"服务卸载成功")
        if result.stdout:
            try:
                # 尝试使用utf-8编码解码输出
                stdout_str = result.stdout.decode('utf-8', errors='replace').strip()
                # 过滤掉不可打印字符
                stdout_str = ''.join(c for c in stdout_str if c.isprintable() or c.isspace())
                # 移除多余的空格
                import re
                stdout_str = re.sub(r'\s+', ' ', stdout_str)
                # 进一步过滤掉无法被GBK编码的字符
                stdout_str = stdout_str.encode('gbk', errors='ignore').decode('gbk')
                if stdout_str:
                    logger.info(f"命令输出: {stdout_str}")
            except Exception:
                # 如果解码失败，忽略输出
                pass
    except subprocess.CalledProcessError as e:
        logger.error(f"服务卸载失败")
        logger.error(f"命令返回码: {e.returncode}")
        if e.stdout:
            try:
                stdout_str = e.stdout.decode('utf-8', errors='replace').strip()
                # 过滤掉不可打印字符
                stdout_str = ''.join(c for c in stdout_str if c.isprintable() or c.isspace())
                # 移除多余的空格
                import re
                stdout_str = re.sub(r'\s+', ' ', stdout_str)
                if stdout_str:
                    logger.error(f"标准输出: {stdout_str}")
            except:
                pass
        if e.stderr:
            try:
                stderr_str = e.stderr.decode('utf-8', errors='replace').strip()
                # 过滤掉不可打印字符
                stderr_str = ''.join(c for c in stderr_str if c.isprintable() or c.isspace())
                # 移除多余的空格
                import re
                stderr_str = re.sub(r'\s+', ' ', stderr_str)
                if stderr_str:
                    logger.error(f"错误输出: {stderr_str}")
            except:
                pass
        sys.exit(1)
    
    logger.info(f"Windows服务卸载完成: {SERVICE_NAME}")


def main():
    """主函数"""
    logger.info("=== Django服务安装脚本 ===")
    
    # 检查是否以管理员身份运行
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False
    
    if not is_admin:
        logger.error("请以管理员身份运行此脚本！")
        logger.error("右键点击脚本文件，选择'以管理员身份运行'")
        sys.exit(1)
    
    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall_nssm_service()
    else:
        install_nssm_service()

if __name__ == "__main__":
    main()
