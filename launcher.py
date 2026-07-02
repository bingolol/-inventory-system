"""进销存管理系统 - 启动器

PyInstaller 打包入口脚本。双击运行时：
1. 初始化工作区目录（%APPDATA%/进销存管理系统）
2. 检测端口冲突，自动选择可用端口（8000~8099）
3. 将选定端口写入 port.txt（供外部工具读取）
4. 启动 FastAPI 后端服务（后台线程）
5. 打开 pywebview 原生窗口访问系统

注意：使用 OS 原生 WebView2 渲染，无需安装浏览器。
"""

import sys
import os
import socket
import threading
import time
import logging
import traceback

# 将 backend 目录加入 Python 路径
if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
    sys.path.insert(0, os.path.join(_base, 'backend'))
else:
    _base = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(_base, 'backend'))

DEFAULT_PORT = 8000
MAX_PORT_TRIES = 100


def setup_logging():
    """配置日志输出"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


def is_port_available(port: int) -> bool:
    """检测指定端口是否可用（未被其他进程监听）"""
    for host in ('127.0.0.1', '0.0.0.0'):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
            except OSError:
                return False
    return True


def find_available_port(start: int = DEFAULT_PORT, max_tries: int = MAX_PORT_TRIES) -> int:
    """从 start 端口开始，逐个检测直到找到可用端口"""
    for port in range(start, start + max_tries):
        if is_port_available(port):
            return port
    raise RuntimeError(
        f"在端口 {start}~{start + max_tries - 1} 范围内未找到可用端口，"
        f"请检查是否有其他程序占用或手动指定端口（设置环境变量 INVENTORY_PORT）"
    )


def save_port(port: int):
    """将运行端口写入工作区 port.txt 文件"""
    import workspace
    port_path = workspace.get_port_path()
    try:
        with open(port_path, 'w', encoding='utf-8') as f:
            f.write(str(port))
        logger = logging.getLogger("launcher")
        logger.info(f"端口信息已写入: {port_path} (port={port})")
    except Exception as e:
        logging.getLogger("launcher").warning(f"写入端口文件失败: {e}")


def wait_for_server(port: int, timeout: int = 30):
    """等待后端服务就绪，轮询 /api/health"""
    import urllib.request
    url = f"http://127.0.0.1:{port}/api/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"后端服务启动超时（{timeout}s）")


def run_backend(port: int):
    """在后台线程中运行 uvicorn 后端服务"""
    import workspace
    import uvicorn
    from main import app

    # console=False (PyInstaller) 下 sys.stdout/stderr 可能为 None，
    # uvicorn 的 ColourizedFormatter 会调用 sys.stderr.isatty() 导致崩溃。
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')

    # 确保工作区目录存在
    workspace.ensure_workspace()

    # 添加文件日志
    log_path = workspace.get_log_path()
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    logging.getLogger().addHandler(file_handler)

    logger = logging.getLogger("launcher")
    logger.info("=" * 50)
    logger.info("进销存管理系统启动中...")
    logger.info(f"工作区目录: {workspace.get_workspace_root()}")
    logger.info(f"数据库路径: {workspace.get_db_path()}")
    logger.info(f"服务端口: {port}")
    logger.info("=" * 50)

    # 将选定端口写入文件
    save_port(port)

    # 自定义 log_config，绕过 uvicorn 默认的 ColourizedFormatter
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": logging.Formatter,
                "fmt": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            },
            "access": {
                "()": logging.Formatter,
                "fmt": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }

    # 启动 uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", log_config=log_config)


def _write_crash_log(error_msg: str):
    """将致命错误写入日志文件和桌面崩溃报告"""
    import workspace

    # 1. 写入工作区日志
    try:
        workspace.ensure_workspace()
        log_path = workspace.get_log_path()
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n[致命错误] {error_msg}\n{'='*50}\n")
    except Exception:
        pass

    # 2. 在桌面写入崩溃报告
    try:
        desktop = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'Desktop')
        crash_file = os.path.join(desktop, '进销存管理系统_启动失败.txt')
        with open(crash_file, 'w', encoding='utf-8') as f:
            f.write(f"进销存管理系统启动失败\n")
            f.write(f"{'='*50}\n")
            f.write(f"错误信息:\n{error_msg}\n")
            f.write(f"{'='*50}\n")
            f.write(f"\n如需帮助，请将此文件发送给技术支持。\n")
            f.write(f"日志文件位置: {workspace.get_log_path()}\n")
    except Exception:
        pass


def main():
    """主入口：检测端口 → 启动后端 → 打开原生窗口"""
    setup_logging()
    logger = logging.getLogger("launcher")

    # ── 1. 确定端口 ──
    env_port = os.environ.get('INVENTORY_PORT')
    if env_port:
        try:
            selected_port = int(env_port)
            logger.info(f"使用环境变量指定端口: {selected_port}")
        except ValueError:
            logger.error(f"环境变量 INVENTORY_PORT='{env_port}' 不是有效端口号，将自动检测")
            selected_port = None
    else:
        selected_port = None

    if selected_port is None:
        try:
            selected_port = find_available_port()
            if selected_port != DEFAULT_PORT:
                logger.info(f"端口 {DEFAULT_PORT} 已被占用，自动切换到 {selected_port}")
            else:
                logger.info(f"使用默认端口 {DEFAULT_PORT}")
        except RuntimeError as e:
            logger.error(str(e))
            _write_crash_log(str(e))
            sys.exit(1)

    # ── 2. 后台启动 uvicorn ──
    server_thread = threading.Thread(target=run_backend, args=(selected_port,), daemon=True)
    server_thread.start()

    # ── 3. 等待服务就绪 ──
    try:
        wait_for_server(selected_port)
        logger.info("后端服务已就绪，正在打开应用窗口...")
    except TimeoutError as e:
        logger.error(str(e))
        _write_crash_log(str(e))
        input("\n按回车键退出...")
        sys.exit(1)

    # ── 4. 创建 pywebview 原生窗口 ──
    try:
        import webview
        window = webview.create_window(
            title="进销存管理系统",
            url=f"http://127.0.0.1:{selected_port}",
            width=1280,
            height=800,
            resizable=True,
            fullscreen=False,
            min_size=(1024, 600),
            text_select=True,
        )
        webview.start(
            debug=os.environ.get('WEBVIEW_DEBUG', '0') == '1',
            private_mode=False,
        )
    except ImportError:
        logger.warning("pywebview 未安装，切换到浏览器模式...")
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{selected_port}")
    except Exception as e:
        error_detail = f"窗口创建失败: {e}\n\n{traceback.format_exc()}"
        logger.error(error_detail)
        _write_crash_log(error_detail)
        input("\n按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
