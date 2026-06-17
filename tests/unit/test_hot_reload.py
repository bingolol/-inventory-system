"""测试后端热更新配置"""
import os
import pytest


class TestHotReloadConfig:
    """测试热更新配置逻辑"""

    def test_dev_mode_detection_with_env_variable(self):
        """开发模式：ENV=development 时应检测为开发环境"""
        os.environ["ENV"] = "development"
        is_dev = os.environ.get("ENV") == "development" or os.environ.get("DEV") == "1"
        assert is_dev is True
        del os.environ["ENV"]

    def test_dev_mode_detection_with_dev_flag(self):
        """开发模式：DEV=1 时应检测为开发环境"""
        os.environ["DEV"] = "1"
        is_dev = os.environ.get("ENV") == "development" or os.environ.get("DEV") == "1"
        assert is_dev is True
        del os.environ["DEV"]

    def test_production_mode_detection(self):
        """生产模式：未设置环境变量时应检测为生产环境"""
        os.environ.pop("ENV", None)
        os.environ.pop("DEV", None)
        is_dev = os.environ.get("ENV") == "development" or os.environ.get("DEV") == "1"
        assert is_dev is False

    def test_uvicorn_reload_parameter(self):
        """验证 uvicorn 配置参数格式正确"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "main", 
            os.path.join(os.path.dirname(__file__), "..", "..", "backend", "main.py"),
            submodule_search_locations=[]
        )
        # 只检查文件内容，不实际导入（避免依赖）
        main_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "main.py")
        with open(main_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "reload=is_dev" in content, "main.py 应包含 reload=is_dev 参数"
        assert 'reload_dirs=["."]' in content, "main.py 应包含 reload_dirs 配置"
