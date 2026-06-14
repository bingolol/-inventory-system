import os
import sqlite3
import shutil
import zipfile
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

import workspace

router = APIRouter()

# 通过 workspace 模块获取路径，支持打包模式
BACKUP_ROOT = workspace.get_backup_dir()
DB_PATH = workspace.get_db_path()
UPLOADS_DIR = workspace.get_uploads_root()
PDFS_DIR = workspace.get_pdfs_dir()
MAX_BACKUPS = 12  # 保留最近 12 份（约 3 个月）


def _backup_db(db_path: str, backup_path: str):
    """使用 SQLite 内置 backup API，保证在线一致性"""
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(backup_path)
    src.backup(dst)
    dst.close()
    src.close()


def _verify_db(db_path: str) -> bool:
    """验证备份文件完整性"""
    conn = sqlite3.connect(db_path)
    result = conn.execute("PRAGMA integrity_check").fetchone()
    conn.close()
    return result[0] == "ok"


@router.post("/hot")
def hot_backup():
    """执行一次热备份：SQLite backup API + 图片 + PDF → zip"""
    os.makedirs(BACKUP_ROOT, exist_ok=True)

    now = datetime.now()
    week_label = now.strftime("%Y-W%W_%H%M%S")  # 如 2026-W17_122800
    backup_dir = os.path.join(BACKUP_ROOT, f"temp_{week_label}")
    os.makedirs(backup_dir, exist_ok=True)

    try:
        # 1. SQLite backup API 导出数据库
        db_backup = os.path.join(backup_dir, "inventory.db")
        _backup_db(DB_PATH, db_backup)

        # 2. 验证完整性
        if not _verify_db(db_backup):
            shutil.rmtree(backup_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail="备份验证失败，数据库完整性检查未通过")

        # 3. 复制图片
        if os.path.exists(UPLOADS_DIR):
            shutil.copytree(UPLOADS_DIR, os.path.join(backup_dir, "uploads"), dirs_exist_ok=True)

        # 4. 复制 PDF
        if os.path.exists(PDFS_DIR):
            shutil.copytree(PDFS_DIR, os.path.join(backup_dir, "pdfs"), dirs_exist_ok=True)

        # 5. 压缩成 zip
        zip_path = os.path.join(BACKUP_ROOT, f"{week_label}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(backup_dir):
                for f in files:
                    file_path = os.path.join(root, f)
                    arcname = os.path.relpath(file_path, backup_dir)
                    zf.write(file_path, arcname)

        # 6. 删除临时目录
        shutil.rmtree(backup_dir, ignore_errors=True)

        # 7. 清理旧备份（保留最近 MAX_BACKUPS 个）
        zips = sorted(Path(BACKUP_ROOT).glob("*.zip"))
        for old_zip in zips[:-MAX_BACKUPS]:
            old_zip.unlink()

        zip_size = os.path.getsize(zip_path) / 1024
        return {
            "status": "ok",
            "backup_file": f"{week_label}.zip",
            "size_kb": round(zip_size, 1),
            "message": f"热备份完成: {week_label}.zip ({zip_size:.1f}KB)"
        }

    except HTTPException:
        raise
    except Exception as e:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"热备份失败: {str(e)}")


@router.get("/list")
def list_backups():
    """列出所有已有备份"""
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    zips = sorted(Path(BACKUP_ROOT).glob("*.zip"), reverse=True)
    return [
        {
            "filename": z.name,
            "size_kb": round(z.stat().st_size / 1024, 1),
            "created_at": datetime.fromtimestamp(z.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        }
        for z in zips
    ]


@router.get("/download/{filename}")
def download_backup(filename: str):
    """下载指定备份文件"""
    file_path = os.path.join(BACKUP_ROOT, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")
    # 防路径穿越
    if not os.path.realpath(file_path).startswith(os.path.realpath(BACKUP_ROOT)):
        raise HTTPException(status_code=403, detail="非法路径")
    return FileResponse(file_path, filename=filename, media_type="application/zip")