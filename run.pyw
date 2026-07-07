"""进销存管理系统 - 桌面客户端启动器

双击运行即可：
1. 显示精美的启动画面（带图标、进度动画）
2. 后台线程启动 FastAPI 后端（跳过硬约束检查，快速启动）
3. 等待服务就绪后关闭启动画面
4. 打开 pywebview 原生桌面窗口（非浏览器）

使用 .pyw 扩展名，不会弹出黑色控制台窗口。
"""

import sys
import os
import time
import socket
import threading
import subprocess
import urllib.request
import logging

# ── 路径配置 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
ICON_PATH = os.path.join(BASE_DIR, "app_icon.ico")
PORT = 8000
BACKEND_URL = f"http://127.0.0.1:{PORT}"
HEALTH_URL = f"{BACKEND_URL}/api/health"
# 后端子进程用 python.exe（不是 pythonw.exe），避免 stdout/stderr=None 导致崩溃
_pythonw = sys.executable
_python_dir = os.path.dirname(_pythonw)
_python_exe = os.path.join(_python_dir, "python.exe")
PYTHON_EXE = _python_exe if os.path.exists(_python_exe) else _pythonw

# 将 backend 目录加入 Python 路径
sys.path.insert(0, BACKEND_DIR)

# ── 颜色主题 ──
COLOR_BG = "#1a1a2e"
COLOR_CARD = "#16213e"
COLOR_ACCENT = "#e94560"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_DIM = "#8892b0"
COLOR_SUCCESS = "#64ffda"
COLOR_ERROR = "#ff6b6b"


class SplashWindow:
    """启动画面窗口（tkinter 无边框窗口）"""

    def __init__(self):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = tk.Tk()
        self.root.title("进销存管理系统")
        self.root.overrideredirect(True)

        # 窗口尺寸和居中
        win_w, win_h = 460, 340
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.configure(bg=COLOR_BG)
        self.root.attributes("-topmost", True)

        # 设置窗口图标
        self._set_icon()

        self._build_ui()

    def _set_icon(self):
        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(default=ICON_PATH)
            except Exception:
                pass

    def _build_ui(self):
        tk = self.tk
        ttk = self.ttk

        main = tk.Frame(self.root, bg=COLOR_BG, padx=40, pady=30)
        main.pack(fill="both", expand=True)

        # ── 图标 ──
        icon_lbl = tk.Label(
            main, text="\U0001F4E6", font=("Segoe UI Emoji", 52),
            bg=COLOR_BG, fg=COLOR_ACCENT,
        )
        icon_lbl.pack(pady=(10, 5))

        # ── 标题 ──
        tk.Label(
            main, text="进销存管理系统",
            font=("Microsoft YaHei UI", 18, "bold"),
            bg=COLOR_BG, fg=COLOR_TEXT,
        ).pack(pady=(0, 4))

        # ── 副标题 ──
        tk.Label(
            main, text="Inventory Management System",
            font=("Segoe UI", 9),
            bg=COLOR_BG, fg=COLOR_TEXT_DIM,
        ).pack(pady=(0, 22))

        # ── 状态文字 ──
        self.status_var = tk.StringVar(value="正在初始化...")
        self.status_label = tk.Label(
            main, textvariable=self.status_var,
            font=("Microsoft YaHei UI", 10),
            bg=COLOR_BG, fg=COLOR_SUCCESS,
        )
        self.status_label.pack(pady=(0, 12))

        # ── 进度条 ──
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=COLOR_CARD,
            background=COLOR_ACCENT,
            darkcolor=COLOR_ACCENT,
            lightcolor=COLOR_ACCENT,
            bordercolor=COLOR_CARD,
            thickness=6,
        )
        self.progress = ttk.Progressbar(
            main, style="Custom.Horizontal.TProgressbar",
            mode="indeterminate", length=360,
        )
        self.progress.pack(pady=(0, 15))

        # ── 底部 ──
        tk.Label(
            main, text="v1.0.0  \u00b7  桌面客户端",
            font=("Segoe UI", 8),
            bg=COLOR_BG, fg=COLOR_TEXT_DIM,
        ).pack(side="bottom", pady=(10, 0))

        # ── 鼠标拖动 ──
        def _drag_start(e):
            self.root._dx = e.x
            self.root._dy = e.y

        def _drag_move(e):
            x = self.root.winfo_x() + e.x - self.root._dx
            y = self.root.winfo_y() + e.y - self.root._dy
            self.root.geometry(f"+{x}+{y}")

        for w in (main, icon_lbl):
            w.bind("<Button-1>", _drag_start)
            w.bind("<B1-Motion>", _drag_move)

    def update_status(self, text, color=None):
        """线程安全更新状态"""
        def _do():
            self.status_var.set(text)
            if color:
                self.status_label.config(fg=color)
        self.root.after(0, _do)

    def close(self):
        """关闭启动画面"""
        self.root.after(0, self.root.destroy)

    def run_mainloop(self):
        self.progress.start(12)
        self.root.mainloop()


def _is_port_listening(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def _check_health():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _kill_port(port):
    """杀掉占用指定端口的进程"""
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in result.stdout.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", pid],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                    except Exception:
                        pass
    except Exception:
        pass


def _start_backend():
    """启动后端服务（子进程方式，隐藏窗口）"""
    env = os.environ.copy()
    env["DEV"] = "1"
    env["SKIP_HARD_CONSTRAINTS"] = "1"  # 跳过硬约束检查，加快启动
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        [PYTHON_EXE, "main.py"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
    )
    return proc


def _wait_backend(splash, timeout=60):
    """等待后端就绪"""
    start = time.time()
    while time.time() - start < timeout:
        if _check_health():
            return True
        elapsed = int(time.time() - start)
        dots = "." * ((elapsed % 3) + 1)
        splash.update_status(f"正在启动服务{dots}", COLOR_SUCCESS)
        time.sleep(1)
    return False


def _open_webview_window(port):
    """打开 pywebview 原生桌面窗口"""
    import webview

    url = f"http://127.0.0.1:{port}"

    window = webview.create_window(
        title="进销存管理系统",
        url=url,
        width=1280,
        height=800,
        resizable=True,
        fullscreen=False,
        min_size=(1024, 600),
        text_select=True,
    )

    webview.start(
        debug=os.environ.get("WEBVIEW_DEBUG", "0") == "1",
        private_mode=False,
        # 设置应用图标
        icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
    )


def main():
    """主入口：启动画面 → 后端 → pywebview 原生窗口"""

    # ── 1. 如果后端已经在运行，直接打开窗口 ──
    if _check_health():
        _open_webview_window(PORT)
        return

    # ── 2. 创建启动画面 ──
    splash = SplashWindow()

    # ── 3. 后台线程执行启动序列 ──
    def _startup_thread():
        # 清理旧端口占用
        if _is_port_listening(PORT):
            splash.update_status("正在清理环境...", COLOR_TEXT_DIM)
            _kill_port(PORT)
            time.sleep(2)

        # 启动后端
        splash.update_status("正在启动后端服务...", COLOR_SUCCESS)
        try:
            _start_backend()
        except Exception as e:
            splash.update_status(f"启动失败: {e}", COLOR_ERROR)
            time.sleep(3)
            splash.close()
            return

        # 等待就绪
        splash.update_status("等待服务就绪...", COLOR_SUCCESS)
        if not _wait_backend(splash):
            splash.update_status("启动超时，请检查日志", COLOR_ERROR)
            time.sleep(3)
            splash.close()
            return

        # 就绪
        splash.update_status("服务已就绪，正在打开窗口...", COLOR_SUCCESS)
        time.sleep(0.8)

        # 关闭启动画面，打开 pywebview 窗口
        splash.close()

        # 在主线程中打开 webview（必须在主线程）
        # 通过 after 回调确保在 tk mainloop 退出后执行
        # webview.start() 会阻塞直到窗口关闭

    thread = threading.Thread(target=_startup_thread, daemon=True)
    thread.start()

    # 运行启动画面主循环（阻塞直到 splash.close() 被调用）
    splash.run_mainloop()

    # 启动画面已关闭，等待线程完成
    thread.join(timeout=2)

    # ── 4. 打开 pywebview 原生桌面窗口 ──
    if _check_health():
        _open_webview_window(PORT)
    else:
        # 后端没起来，显示错误
        import tkinter.messagebox as mb
        mb.showerror(
            "启动失败",
            "后端服务未能正常启动。\n请检查日志文件：\n" + os.path.join(BACKEND_DIR, "app.log"),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
