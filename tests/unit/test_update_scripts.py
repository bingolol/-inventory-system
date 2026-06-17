"""测试更新脚本"""
import os
import pytest


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


class TestUpdateScripts:
    """测试一键更新脚本"""

    def test_update_script_exists(self):
        """更新系统.bat 应存在"""
        path = os.path.join(SCRIPTS_DIR, "更新系统.bat")
        assert os.path.exists(path), "更新系统.bat 应存在"

    def test_update_script_contains_git_pull(self):
        """更新系统.bat 应包含 git pull"""
        path = os.path.join(SCRIPTS_DIR, "更新系统.bat")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "git pull" in content, "更新系统.bat 应包含 git pull"

    def test_update_script_contains_npm_install(self):
        """更新系统.bat 应包含 npm install"""
        path = os.path.join(SCRIPTS_DIR, "更新系统.bat")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "npm install" in content, "更新系统.bat 应包含 npm install"

    def test_update_script_contains_python_main(self):
        """更新系统.bat 应包含 python main.py"""
        path = os.path.join(SCRIPTS_DIR, "更新系统.bat")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "python main.py" in content, "更新系统.bat 应包含 python main.py"

    def test_quick_update_script_exists(self):
        """仅更新代码.bat 应存在"""
        path = os.path.join(SCRIPTS_DIR, "仅更新代码.bat")
        assert os.path.exists(path), "仅更新代码.bat 应存在"

    def test_quick_update_script_contains_git_pull(self):
        """仅更新代码.bat 应包含 git pull"""
        path = os.path.join(SCRIPTS_DIR, "仅更新代码.bat")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "git pull" in content, "仅更新代码.bat 应包含 git pull"

    def test_quick_update_no_python_main(self):
        """仅更新代码.bat 不应启动服务"""
        path = os.path.join(SCRIPTS_DIR, "仅更新代码.bat")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "python main.py" not in content, "仅更新代码.bat 不应包含 python main.py"
