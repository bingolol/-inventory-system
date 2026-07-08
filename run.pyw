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

# ── 关键：pythonw.exe 下 sys.stdout/stderr 为 None，任何库内部 print/write 都会静默崩溃 ──
# 必须在所有其他导入（urllib、subprocess、logging 等）之前重定向到 devnull
# 参考：https://cloud.tencent.com/developer/ask/sof/102015830
if sys.platform == "win32" and os.path.basename(sys.executable).lower() == "pythonw.exe":
    _devnull = open(os.devnull, "w")
    sys.stdout = _devnull
    sys.stderr = _devnull

import time
import socket
import threading
import subprocess
import urllib.request
import atexit
import signal

# ── 全局后端进程引用（供 atexit / 信号处理兜底清理）──
_backend_proc = None

# ── 全局唯一实例互斥体句柄（保持引用，防止 GC 释放导致锁失效）──
_mutex_handle = None

# ── 路径配置 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
ICON_PATH = os.path.join(BASE_DIR, "app_icon.ico")
PORT = 8000
HEALTH_URL = f"http://127.0.0.1:{PORT}/api/health"
LOG_FILE = os.path.join(BACKEND_DIR, "launcher.log")        # 启动器自身日志
BACKEND_OUT_FILE = os.path.join(BACKEND_DIR, "backend_stdout.log")  # 后端 stdout/stderr（进度监控读取此文件）

# 后端子进程用 python.exe（不是 pythonw.exe），避免 stdout/stderr=None 导致崩溃
_pythonw = sys.executable
_python_dir = os.path.dirname(_pythonw)
_python_exe = os.path.join(_python_dir, "python.exe")
PYTHON_EXE = _python_exe if os.path.exists(_python_exe) else _pythonw

# ── 颜色主题 ──
COLOR_BG = "#1a1a2e"
COLOR_CARD = "#16213e"
COLOR_ACCENT = "#e94560"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_DIM = "#8892b0"
COLOR_SUCCESS = "#64ffda"
COLOR_ERROR = "#ff6b6b"


def _log(msg):
    """写入启动器日志（独立文件，避免与后端 stdout 文件锁冲突）"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _acquire_single_instance_lock():
    """尝试获取全局唯一实例锁（Windows 命名互斥体）。

    利用 kernel32.CreateMutexW 创建系统级命名互斥体：
    - 首次调用：创建互斥体，返回 handle
    - 已有实例：GetLastError 返回 ERROR_ALREADY_EXISTS，返回 None

    互斥体是内核对象，进程崩溃时 OS 自动释放，不会死锁。
    调用方必须将返回的 handle 保存在全局变量中，
    否则 Python GC 回收 handle 会导致互斥体提前释放。
    """
    global _mutex_handle
    if sys.platform != "win32":
        return True  # 非 Windows 暂不限制

    import ctypes

    ERROR_ALREADY_EXISTS = 183
    kernel32 = ctypes.windll.kernel32

    mutex_name = "Global\\进销存管理系统_桌面客户端_SingleInstance"
    handle = kernel32.CreateMutexW(None, False, mutex_name)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        _log("检测到已有实例在运行（命名互斥体已存在）")
        return None

    _mutex_handle = handle  # 保活，防止 GC 释放
    _log(f"已获取全局唯一实例锁, handle={handle}")
    return handle


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

        # ── 进度条（按阶段递进，非无限滚动）──
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
            mode="determinate", length=360, maximum=100,
        )
        self.progress.pack(pady=(0, 6))

        # ── 阶段指示器 ──
        self.stage_var = tk.StringVar(value="")
        self.stage_label = tk.Label(
            main, textvariable=self.stage_var,
            font=("Microsoft YaHei UI", 8),
            bg=COLOR_BG, fg=COLOR_TEXT_DIM,
        )
        self.stage_label.pack(pady=(0, 15))

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

    def update_progress(self, pct, stage_text=""):
        """线程安全更新进度条和阶段文本"""
        def _do():
            self.progress['value'] = pct
            self.stage_var.set(stage_text)
        self.root.after(0, _do)

    def close(self):
        """关闭启动画面"""
        self.root.after(0, self.root.destroy)

    def run_mainloop(self):
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


def _terminate_process_tree(pid):
    """终止进程树（包括所有子进程），确保后端彻底退出"""
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _log(f"进程树已终止, PID={pid}")
    except Exception as e:
        _log(f"终止进程树失败 PID={pid}: {e}")


def _cleanup_backend():
    """清理后端进程 — 窗口关闭后调用，atexit 兜底"""
    global _backend_proc
    if _backend_proc is not None:
        rc = _backend_proc.poll()
        if rc is None:  # 进程仍在运行
            _log(f"正在终止后端进程 PID={_backend_proc.pid}...")
            _terminate_process_tree(_backend_proc.pid)
            try:
                _backend_proc.wait(timeout=5)
            except Exception:
                pass
        else:
            _log(f"后端进程已自行退出, returncode={rc}")
        _backend_proc = None


def _start_backend():
    """启动后端服务（子进程方式，隐藏窗口，stderr 写入日志文件）

    不使用 DETACHED_PROCESS — 后端进程生命周期由启动器管理，
    窗口关闭时自动终止，atexit + 信号处理双重兜底。
    """
    env = os.environ.copy()
    # 只跳过硬约束检查，不设 DEV=1（DEV=1 会触发 uvicorn reload 热重载，
    # 生产环境 watchfiles 不停扫描会导致卡顿/无限重载）
    env["SKIP_HARD_CONSTRAINTS"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    # stdout/stderr 写入独立文件（不与 launcher.log 混用，避免 Windows 文件锁冲突）
    # 用二进制模式打开——子进程输出是 GBK 字节流，启动器写入用 UTF-8 编码的字节
    err_log = open(BACKEND_OUT_FILE, "ab")
    err_log.write(f"\n{'='*50}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 后端启动\n{'='*50}\n".encode("utf-8"))
    err_log.flush()

    proc = subprocess.Popen(
        [PYTHON_EXE, "main.py"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=err_log,
        stderr=err_log,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    # 关闭启动器侧的文件句柄——子进程已继承独立的 fd，不受影响。
    # 必须关闭，否则 Windows 文件锁会阻止 _wait_backend() 读取此文件。
    err_log.close()

    _log(f"后端进程已启动, PID={proc.pid}, python={PYTHON_EXE}")
    return proc


# ── 启动阶段映射表：后端日志关键词 → 用户友好的进度文案 ──
# 基于后端实际日志输出（backend_stdout.log 中 stdout/stderr 重定向的内容）
# 按进度排序，越后面匹配到的阶段会覆盖前面的
_PROGRESS_STAGES = [
    # (日志关键词列表, 状态文案, 阶段说明, 进度百分比)
    (["Started server process", "Waiting for application startup"],
     "正在启动服务进程...", "步骤 1/4 · 进程初始化", 10),
    (["ImmutableTriggers", "CREATE TABLE", "init_db", "maintenance_mode"],
     "正在初始化数据库...", "步骤 2/4 · 数据库初始化", 30),
    (["ConfirmStore", "confirm_store", "EventBus", "register_middleware",
      "Truth Source", "不变量", "审计"],
     "正在加载业务模块...", "步骤 3/4 · 模块加载", 65),
    (["启动完成", "Application startup complete", "Uvicorn running"],
     "服务即将就绪...", "步骤 4/4 · 启动服务", 90),
]


def _match_progress_stage(log_text):
    """从日志文本匹配当前启动阶段，返回 (状态文案, 阶段说明, 进度百分比) 或 None"""
    best = None
    for keywords, status, stage, pct in _PROGRESS_STAGES:
        for kw in keywords:
            if kw in log_text:
                best = (status, stage, pct)
                break  # 匹配到当前阶段，继续看后面有没有更靠后的阶段
    return best


def _wait_backend(splash, proc, timeout=45):
    """等待后端就绪，监控日志展示阶段性进度，检测进程崩溃"""
    start = time.time()
    last_stage_pct = 0
    log_offset = 0  # 已读取的日志偏移量

    # 记录后端启动前的日志文件大小，只读新增部分
    try:
        log_offset = os.path.getsize(BACKEND_OUT_FILE)
    except Exception:
        log_offset = 0

    while time.time() - start < timeout:
        # ── 检测后端进程是否已经退出（说明崩溃了）──
        rc = proc.poll()
        if rc is not None:
            _log(f"后端进程已退出, returncode={rc}")
            error_tail = _read_log_tail(15)
            splash.update_status(f"后端启动失败 (code={rc})", COLOR_ERROR)
            splash.update_progress(100, f"启动失败 (exit code {rc})")
            time.sleep(2)
            return ("crash", error_tail)

        # ── 读取后端 stdout 日志新增内容，匹配启动阶段 ──
        try:
            current_size = os.path.getsize(BACKEND_OUT_FILE)
            if current_size > log_offset:
                with open(BACKEND_OUT_FILE, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(log_offset)
                    new_content = f.read()
                    log_offset = current_size

                stage_info = _match_progress_stage(new_content)
                if stage_info and stage_info[2] > last_stage_pct:
                    status_msg, stage_text, pct = stage_info
                    last_stage_pct = pct
                    splash.update_status(status_msg, COLOR_SUCCESS)
                    splash.update_progress(pct, stage_text)
                    _log(f"进度更新: {stage_text} ({pct}%)")
        except Exception:
            pass

        # ── 健康检查 ──
        if _check_health():
            _log("后端健康检查通过")
            splash.update_progress(100, "就绪")
            return ("ok", None)

        # ── 时间兜底：如果日志阶段没更新，用时间模拟进度 ──
        elapsed = int(time.time() - start)
        if last_stage_pct == 0 and elapsed > 3:
            # 3 秒后还没匹配到任何日志阶段，显示通用进度
            splash.update_status("正在启动服务...", COLOR_SUCCESS)
            splash.update_progress(min(20 + elapsed, 50), f"正在启动... ({elapsed}s)")

        time.sleep(0.5)

    _log(f"后端启动超时 ({timeout}s)")
    return ("timeout", _read_log_tail(15))


def _read_log_tail(n=10):
    """读取后端 stdout 日志文件最后 n 行"""
    try:
        with open(BACKEND_OUT_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-n:]) if lines else "(空)"
    except Exception:
        return "(无法读取日志)"


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
        icon=ICON_PATH if os.path.exists(ICON_PATH) else None,
    )


def _show_error(title, detail):
    """显示错误对话框"""
    import tkinter as tk
    import tkinter.messagebox as mb
    root = tk.Tk()
    root.withdraw()
    mb.showerror(title, detail)
    root.destroy()


def _show_info(title, detail):
    """显示提示对话框"""
    import tkinter as tk
    import tkinter.messagebox as mb
    root = tk.Tk()
    root.withdraw()
    mb.showinfo(title, detail)
    root.destroy()


def main():
    """主入口：启动画面 → 后端 → pywebview 原生窗口

    生命周期：启动器退出 = 前端窗口关闭 + 后端进程终止，三者绑定。
    """
    global _backend_proc

    _log("=" * 50)
    _log("启动器开始执行")
    _log(f"BASE_DIR={BASE_DIR}")
    _log(f"PYTHON_EXE={PYTHON_EXE}")
    _log(f"BACKEND_DIR={BACKEND_DIR}")

    # ── 0. 全局唯一实例检查（必须在任何窗口创建之前）──
    if _acquire_single_instance_lock() is None:
        _show_info("进销存管理系统", "程序已在运行中，请勿重复启动。")
        return

    # ── 注册清理兜底 ──
    atexit.register(_cleanup_backend)
    try:
        signal.signal(signal.SIGTERM, lambda *_: (sys.exit(0)))
    except Exception:
        pass  # Windows 对 SIGTERM 支持有限

    # ── 1. 如果后端已经在运行，直接打开窗口（不接管生命周期）──
    if _check_health():
        _log("后端已在运行，直接打开窗口")
        try:
            _open_webview_window(PORT)
        except Exception as e:
            _show_error("启动失败", f"无法打开窗口:\n{e}")
        return

    # ── 2. 创建启动画面 ──
    splash = SplashWindow()
    backend_proc = [None]  # 用 list 包装，方便闭包修改
    startup_result = [None]  # ("ok"|"crash"|"timeout", error_detail)

    # ── 3. 后台线程执行启动序列 ──
    def _startup_thread():
        # 清理旧端口占用
        if _is_port_listening(PORT):
            splash.update_status("正在清理环境...", COLOR_TEXT_DIM)
            _kill_port(PORT)
            time.sleep(2)

        # 启动后端
        splash.update_status("正在启动后端服务...", COLOR_SUCCESS)
        splash.update_progress(5, "正在拉起后端进程...")
        try:
            backend_proc[0] = _start_backend()
        except Exception as e:
            _log(f"启动后端异常: {e}")
            splash.update_status(f"启动失败: {e}", COLOR_ERROR)
            splash.update_progress(100, "启动失败")
            time.sleep(3)
            startup_result[0] = ("error", str(e))
            splash.close()
            return

        # 等待就绪（日志驱动进度展示）
        result, error_detail = _wait_backend(splash, backend_proc[0], timeout=45)

        if result == "ok":
            splash.update_status("服务已就绪，正在打开窗口...", COLOR_SUCCESS)
            time.sleep(0.8)
            startup_result[0] = ("ok", None)
            splash.close()
        elif result == "crash":
            startup_result[0] = ("crash", error_detail)
            splash.close()
        else:
            startup_result[0] = ("timeout", error_detail)
            splash.close()

    thread = threading.Thread(target=_startup_thread, daemon=True)
    thread.start()

    # 运行启动画面主循环（阻塞直到 splash.close() 被调用）
    splash.run_mainloop()

    # 启动画面已关闭，等待线程完成
    thread.join(timeout=3)

    # ── 4. 根据启动结果决定下一步 ──
    result = startup_result[0]

    if result and result[0] == "ok" and _check_health():
        # 后端就绪 — 将进程引用提升到全局，窗口关闭后清理
        _backend_proc = backend_proc[0]
        _log("前端窗口即将打开，后端生命周期已绑定")

        # 打开 pywebview 窗口（阻塞，直到用户关闭窗口）
        try:
            _open_webview_window(PORT)
        except ImportError:
            _show_error(
                "缺少依赖",
                "pywebview 未安装，请运行：\n\npip install pywebview\n\n"
                "安装后重新启动系统。",
            )
        except Exception as e:
            _show_error("窗口创建失败", str(e))
        finally:
            # ── 窗口已关闭（或异常），终止后端进程 ──
            _log("前端窗口已关闭，正在终止后端进程...")
            _cleanup_backend()
            _log("后端已终止，启动器退出")
    else:
        # 后端没起来 — 如果进程还残留也清掉
        if backend_proc[0] is not None:
            _backend_proc = backend_proc[0]
            _cleanup_backend()

        error_detail = result[1] if result else "未知错误"
        _show_error(
            "后端启动失败",
            f"后端服务未能正常启动。\n\n"
            f"错误日志（最后10行）：\n"
            f"{'-'*40}\n"
            f"{error_detail}\n"
            f"{'-'*40}\n\n"
            f"启动器日志：{LOG_FILE}\n"
            f"后端输出：{BACKEND_OUT_FILE}\n"
            f"后端应用日志：{os.path.join(BACKEND_DIR, 'app.log')}",
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # pythonw.exe 下 sys.stderr=None，未捕获异常会静默崩溃
        import traceback
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n[致命错误] 启动器崩溃:\n{traceback.format_exc()}\n")
        except Exception:
            pass
        try:
            import tkinter as tk
            import tkinter.messagebox as mb
            root = tk.Tk()
            root.withdraw()
            mb.showerror("启动器崩溃", traceback.format_exc())
            root.destroy()
        except Exception:
            pass
