import os
import time
import subprocess

def wait_for_t_drive(timeout=180, interval=5):
    """
    等待 T 盘可访问
    :param timeout: 总等待时间（秒）
    :param interval: 尝试间隔（秒）
    :return: 成功与否
    """
    print("正在检测 T 盘是否可访问...")
    max_attempts = timeout // interval
    attempt = 0

    while attempt < max_attempts:
        try:
            if os.path.exists("T:\\"):
                print("T 盘已就绪，继续执行程序。")
                return True
        except Exception as e:
            print(f"访问 T 盘失败：{e}")

        attempt += 1
        print(f"第 {attempt} 次尝试失败，{interval} 秒后再次尝试...")
        time.sleep(interval)

    print("超过最大尝试时间，T 盘仍然不可访问，程序退出。")
    return False


def main():
    # 等待 T 盘就绪
    if not wait_for_t_drive():
        input("按任意键退出...")
        return

    # 设置项目路径（请确认路径是否可访问）
    project_path = r"T:\Servo Gun\release"
    
    # 切换到项目目录
    try:
        os.chdir(project_path)
    except FileNotFoundError:
        print(f"找不到路径：{project_path}，请检查网络连接或路径是否正确。")
        input("按任意键退出...")
        return

    # 检查 manage.py 是否存在
    if not os.path.isfile("manage.py"):
        print("找不到 manage.py 文件，请确认路径是否正确。")
        input("按任意键退出...")
        return

    # 检查虚拟环境是否存在
    venv_activate = os.path.join("venv", "Scripts", "activate")
    if not os.path.exists(venv_activate):
        print("找不到虚拟环境，请确认 venv 是否存在。")
        input("按任意键退出...")
        return

    # 激活虚拟环境并运行服务器
    print("正在启动 Django 服务器...")
    activate_script = os.path.join("venv", "Scripts", "activate.bat")

    # 使用 cmd 来运行 activate 并保持窗口
    command = [activate_script, "&&", "python", "manage.py", "runserver", "0.0.0.0:6931"]
    subprocess.run(["cmd", "/k"] + command)

if __name__ == "__main__":
    main()