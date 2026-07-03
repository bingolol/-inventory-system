"""集成测试：运行 docs/操作模板/verify_all_templates.py 验证全部 20 个业务模板

本测试通过 subprocess 调用现有的模板验证脚本，避免重复维护两份相同逻辑。
前置条件：后端服务已启动在 http://127.0.0.1:8000（或 TEMPLATE_BASE_URL 指定地址）。
CI 建议：先启动测试服务器，再执行 pytest tests/integration/test_operation_templates.py。
"""
import os
import subprocess
import sys
import time

import pytest
import requests


def _backend_ready(url: str = "http://127.0.0.1:8000/api/health", timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


@pytest.mark.integration
@pytest.mark.skipif(not _backend_ready(), reason="后端服务未启动，跳过模板集成测试")
def test_operation_templates():
    """端到端跑通 20 个业务模板。"""
    script = os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "操作模板", "verify_all_templates.py"
    )
    script = os.path.abspath(script)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=120,
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    assert result.returncode == 0, (
        f"模板集成测试失败（exit={result.returncode}）\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
