"""进销存管理系统 - 安装向导

双击运行后自动：
1. 显示安装界面（tkinter GUI）
2. 选择安装目录（默认 C:\Program Files\进销存管理系统）
3. 解压程序文件到安装目录
4. 创建桌面快捷方式
5. 创建开始菜单快捷方式
6. 可选：安装完成后立即启动
"""

import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import zipfile

# 安装包内嵌的应用文件目录（PyInstaller 打包时放入 _MEIPASS/app_files/）
APP_NAME = "进销存管理系统"
EXE_NAME = "进销存管理系统.exe"


def get_resource_dir():
    """获取内嵌资源目录"""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'app_files')
    # 开发模式：直接指向 dist2
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist2', APP_NAME)


def create_shortcut(exe_path, shortcut_path, icon_path=None, description=""):
    """使用 PowerShell 创建 .lnk 快捷方式"""
    icon_arg = f"-IconLocation '{icon_path}'" if icon_path and os.path.exists(icon_path) else ""
    ps1 = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{shortcut_path}')
$s.TargetPath = '{exe_path}'
$s.WorkingDirectory = '{os.path.dirname(exe_path)}'
$s.Description = '{description}'
{f"$s.IconLocation = '{icon_path}'" if icon_path and os.path.exists(icon_path) else ""}
$s.Save()
"""
    result = subprocess.run(
        ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps1],
        capture_output=True, text=True
    )
    return result.returncode == 0


class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - 安装向导")
        self.root.geometry("520x380")
        self.root.resizable(False, False)

        # 默认安装目录
        default_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'Programs', APP_NAME)
        self.install_dir = tk.StringVar(value=default_dir)
        self.create_shortcut_var = tk.BooleanVar(value=True)
        self.launch_after_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        # 标题
        title_frame = tk.Frame(self.root, bg="#409EFF", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text=f"安装 {APP_NAME}", font=("Microsoft YaHei", 18, "bold"),
                 bg="#409EFF", fg="white").pack(pady=15)

        # 主内容
        content = tk.Frame(self.root, padx=30, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # 安装目录
        tk.Label(content, text="安装目录：", font=("Microsoft YaHei", 10)).pack(anchor=tk.W)
        dir_frame = tk.Frame(content)
        dir_frame.pack(fill=tk.X, pady=(5, 15))
        tk.Entry(dir_frame, textvariable=self.install_dir, font=("Microsoft YaHei", 9),
                 width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(dir_frame, text="浏览...", command=self._browse_dir,
                  font=("Microsoft YaHei", 9)).pack(side=tk.RIGHT, padx=(5, 0))

        # 选项
        tk.Checkbutton(content, text="创建桌面快捷方式", variable=self.create_shortcut_var,
                       font=("Microsoft YaHei", 10)).pack(anchor=tk.W, pady=2)
        tk.Checkbutton(content, text="安装完成后立即启动", variable=self.launch_after_var,
                       font=("Microsoft YaHei", 10)).pack(anchor=tk.W, pady=2)

        # 进度条
        self.progress = ttk.Progressbar(content, mode='determinate', length=400)
        self.progress.pack(pady=(20, 5))
        self.status_label = tk.Label(content, text="准备安装...", font=("Microsoft YaHei", 9),
                                      fg="#666")
        self.status_label.pack()

        # 按钮区
        btn_frame = tk.Frame(self.root, padx=30, pady=15)
        btn_frame.pack(fill=tk.X)
        self.install_btn = tk.Button(btn_frame, text="安装", command=self._do_install,
                                      font=("Microsoft YaHei", 11), bg="#409EFF", fg="white",
                                      width=12, height=1, cursor="hand2")
        self.install_btn.pack(side=tk.RIGHT)
        tk.Button(btn_frame, text="取消", command=self.root.destroy,
                  font=("Microsoft YaHei", 11), width=8, height=1).pack(side=tk.RIGHT, padx=(0, 10))

    def _browse_dir(self):
        d = filedialog.askdirectory(title="选择安装目录", initialdir=self.install_dir.get())
        if d:
            self.install_dir.set(d)

    def _do_install(self):
        self.install_btn.config(state=tk.DISABLED)
        self.root.update()

        try:
            install_dir = self.install_dir.get()
            src_dir = get_resource_dir()

            # 1. 创建安装目录
            self._update_status("正在创建安装目录...", 10)
            os.makedirs(install_dir, exist_ok=True)

            # 2. 复制文件
            self._update_status("正在复制程序文件...", 30)
            if not os.path.exists(src_dir):
                raise Exception(f"安装包数据不存在: {src_dir}")

            # 复制 _internal 目录和 exe
            items_to_copy = ['_internal', EXE_NAME, 'app_icon.ico']
            total = len(items_to_copy)
            for i, item in enumerate(items_to_copy):
                src = os.path.join(src_dir, item)
                dst = os.path.join(install_dir, item)
                if os.path.exists(src):
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                pct = 30 + int((i + 1) / total * 40)
                self._update_status(f"正在复制 {item}...", pct)

            # 3. 创建桌面快捷方式
            if self.create_shortcut_var.get():
                self._update_status("正在创建桌面快捷方式...", 80)
                exe_path = os.path.join(install_dir, EXE_NAME)
                icon_path = os.path.join(install_dir, 'app_icon.ico')
                desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
                shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")
                create_shortcut(exe_path, shortcut_path, icon_path, APP_NAME)

                # 开始菜单快捷方式
                start_menu = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs')
                start_shortcut = os.path.join(start_menu, f"{APP_NAME}.lnk")
                create_shortcut(exe_path, start_shortcut, icon_path, APP_NAME)

            # 4. 完成
            self._update_status("安装完成！", 100)
            messagebox.showinfo("安装完成",
                f"{APP_NAME} 已成功安装到:\n{install_dir}\n\n"
                f"数据将保存在:\n%APPDATA%\\{APP_NAME}")

            # 5. 可选启动
            if self.launch_after_var.get():
                exe_path = os.path.join(install_dir, EXE_NAME)
                subprocess.Popen([exe_path], cwd=install_dir)

            self.root.destroy()

        except Exception as e:
            messagebox.showerror("安装失败", str(e))
            self.install_btn.config(state=tk.NORMAL)

    def _update_status(self, text, progress):
        self.status_label.config(text=text)
        self.progress['value'] = progress
        self.root.update()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = InstallerApp()
    app.run()