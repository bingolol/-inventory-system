"""创建桌面快捷方式

运行此脚本会在桌面创建一个带图标的快捷方式：
  - 名称: 进销存管理系统
  - 图标: app_icon.ico
  - 目标: pythonw.exe run.pyw（隐藏控制台窗口，pywebview 桌面客户端）

可重复运行，会覆盖旧的快捷方式。
"""

import os
import sys


def create_desktop_shortcut():
    """在桌面创建快捷方式（使用 win32com）"""
    import win32com.client

    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "app_icon.ico")
    pyw_path = os.path.join(base_dir, "run.pyw")

    # 桌面路径
    desktop = os.path.join(
        os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop"
    )
    shortcut_path = os.path.join(desktop, "进销存管理系统.lnk")

    # 找到 pythonw.exe（无控制台窗口的 Python）
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable

    # 用 WScript.Shell COM 对象创建快捷方式
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(shortcut_path)
    shortcut.TargetPath = pythonw
    shortcut.Arguments = pyw_path
    shortcut.WorkingDirectory = base_dir
    shortcut.IconLocation = f"{icon_path}, 0"
    shortcut.Description = "进销存管理系统 - 双击启动"
    shortcut.WindowStyle = 7  # 最小化
    shortcut.Save()

    return shortcut_path


if __name__ == "__main__":
    print("正在创建桌面快捷方式...")
    try:
        path = create_desktop_shortcut()
        print(f"[OK] 桌面快捷方式已创建: {path}")
        print("     双击桌面「进销存管理系统」图标即可启动系统")
    except ImportError:
        print("[错误] 缺少 pywin32，正在安装...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "pywin32"], check=True)
        try:
            path = create_desktop_shortcut()
            print(f"[OK] 桌面快捷方式已创建: {path}")
        except Exception as e:
            print(f"[错误] 创建失败: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"[错误] 创建失败: {e}")
        sys.exit(1)
