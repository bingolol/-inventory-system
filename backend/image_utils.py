"""图片上传/删除工具模块，避免 main.py 循环导入"""
import os
import uuid
import logging

from workspace import get_uploads_dir as _get_uploads_dir

logger = logging.getLogger("inventory")

UPLOAD_DIR = _get_uploads_dir()
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

IMAGE_BASE_URL = "/uploads/images"
BUSINESS_TYPES = {"expense", "personal", "purchase", "sale", "invoice"}
ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/webp": "webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


def generate_filename(business_type: str, record_id: int, ext: str) -> str:
    """生成文件名：{business_type}_{record_id}_{6位随机码}.{ext}"""
    id_part = str(record_id) if record_id > 0 else "temp"
    random_code = uuid.uuid4().hex[:6]
    return f"{business_type}_{id_part}_{random_code}.{ext}"


def save_image_file(content: bytes, filename: str) -> str:
    """保存图片文件，返回 image_url"""
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return f"{IMAGE_BASE_URL}/{filename}"


def delete_old_image(old_image_url: str) -> bool:
    """
    根据image_url删除旧图片文件
    安全校验：只允许删除 UPLOAD_DIR 下的文件，防止路径穿越
    """
    if not old_image_url:
        return False
    try:
        filename = old_image_url.rsplit("/", 1)[-1]
        # 安全校验：文件名必须符合 {type}_{id}_{code}.{ext} 格式
        parts = filename.rsplit(".", 1)
        if len(parts) != 2:
            logger.warning(f"图片文件名格式异常: {filename}")
            return False
        name_part, ext = parts
        segments = name_part.split("_")
        if len(segments) < 3:
            logger.warning(f"图片文件名格式异常: {filename}")
            return False
        if segments[0] not in BUSINESS_TYPES:
            logger.warning(f"图片文件名业务类型异常: {filename}")
            return False

        filepath = os.path.join(UPLOAD_DIR, filename)
        # 防路径穿越：确认真实路径在 UPLOAD_DIR 内
        real_path = os.path.realpath(filepath)
        if not real_path.startswith(os.path.realpath(UPLOAD_DIR)):
            logger.warning(f"路径穿越风险: {filepath}")
            return False

        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"已删除旧图片: {filepath}")
            return True
        return False
    except Exception as e:
        logger.warning(f"删除旧图片失败: {e}")
        return False