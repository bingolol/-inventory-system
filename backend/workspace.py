"""工作区目录配置模块

提供所有数据文件路径的单一来源（AP-8），支持两种运行模式：
1. 开发模式：基于项目源码目录（向后兼容）
2. 打包模式（PyInstaller）：基于用户工作区目录（%APPDATA%/进销存管理系统）

路径优先级：
1. 环境变量 INVENTORY_WORKSPACE（最高优先级，用于自定义部署）
2. 打包模式：sys._MEIPASS 存在时 → %APPDATA%/进销存管理系统
3. 开发模式：项目根目录（向后兼容，不影响现有开发流程）
"""

import os
import sys
import logging

logger = logging.getLogger("inventory")


def is_frozen() -> bool:
    """判断是否在 PyInstaller 打包环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_workspace_root() -> str:
    """获取工作区根目录

    打包模式：C:\\Users\\<用户>\\AppData\\Roaming\\进销存管理系统
    开发模式：<项目根目录>/backend（向后兼容原有数据位置）
    """
    # 1. 环境变量覆盖
    env_ws = os.environ.get('INVENTORY_WORKSPACE')
    if env_ws:
        return env_ws

    if is_frozen():
        # 打包模式：使用 %APPDATA%
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        return os.path.join(app_data, '进销存管理系统')

    # 开发模式：backend/ 目录（向后兼容，数据文件原来就在 backend/ 下）
    return os.path.dirname(os.path.abspath(__file__))


def get_internal_dir() -> str:
    """获取打包内部资源目录（PyInstaller 的 _MEIPASS）

    开发模式下返回项目根目录（frontend/dist 在项目根目录下）
    """
    if is_frozen():
        return sys._MEIPASS
    # 开发模式：返回项目根目录（frontend/dist 的父目录）
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db_path() -> str:
    """数据库文件路径"""
    return os.path.join(get_workspace_root(), 'inventory.db')


def get_uploads_dir() -> str:
    """图片上传目录"""
    return os.path.join(get_workspace_root(), 'uploads', 'images')


def get_uploads_root() -> str:
    """uploads 根目录（用于静态文件挂载）"""
    return os.path.join(get_workspace_root(), 'uploads')


def get_pdfs_dir() -> str:
    """PDF 存储目录"""
    return os.path.join(get_workspace_root(), 'pdfs')


def get_backup_dir() -> str:
    """热备份目录

    开发模式：项目根目录/hot_backup（向后兼容）
    打包模式：工作区根目录/hot_backup
    """
    if is_frozen():
        return os.path.join(get_workspace_root(), 'hot_backup')
    # 开发模式：项目根目录/hot_backup
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hot_backup')


def get_log_path() -> str:
    """日志文件路径"""
    return os.path.join(get_workspace_root(), 'app.log')


def get_port_path() -> str:
    """运行端口记录文件路径（打包模式下供浏览器/外部工具读取实际端口）"""
    return os.path.join(get_workspace_root(), 'port.txt')


def get_frontend_dist_dir() -> str:
    """前端 dist 目录

    打包模式：内嵌在 _MEIPASS/frontend_dist 中
    开发模式：项目根目录/frontend/dist
    """
    return os.path.join(get_internal_dir(), 'frontend', 'dist')


def ensure_workspace():
    """首次运行时自动创建工作区目录结构"""
    dirs = [
        get_workspace_root(),
        get_uploads_dir(),
        get_pdfs_dir(),
        get_backup_dir(),
    ]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
            logger.info(f"工作区目录已创建: {d}")

    # 如果工作区中没有数据库，从内置模板复制（首次安装）
    db_path = get_db_path()
    if is_frozen() and not os.path.exists(db_path):
        # 打包模式下，内置一个空数据库模板（在构建时创建）
        template_db = os.path.join(get_internal_dir(), 'inventory.db.template')
        if os.path.exists(template_db):
            import shutil
            shutil.copy2(template_db, db_path)
            logger.info(f"数据库已从模板创建: {db_path}")


# 启动时打印工作区信息（便于排障）
if is_frozen():
    logger.info(f"打包模式 - 工作区: {get_workspace_root()}")
    logger.info(f"打包模式 - 内部资源: {get_internal_dir()}")
else:
    logger.info(f"开发模式 - 工作区: {get_workspace_root()}")