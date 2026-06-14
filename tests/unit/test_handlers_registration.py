"""事件处理器注册测试 — 确保 handler 正确注册到事件总线"""
import pytest
import handlers  # 触发 handler 注册
from events import get_handlers


class TestHandlerRegistration:
    """验证关键事件至少有一个 handler"""

    @pytest.mark.parametrize("event_name", [
        "sale_order.created",
        "sale_order.cancelled",
        "sale_order.deleted",
    ])
    def test_event_has_handlers(self, event_name):
        hs = get_handlers(event_name)
        assert len(hs) > 0, f"{event_name} should have at least one handler"

    def test_handler_has_priority(self):
        """每个 handler 应有 priority 属性"""
        for evt in ["sale_order.created", "sale_order.cancelled"]:
            for h in get_handlers(evt):
                assert hasattr(h, "priority"), f"Handler {h.name} missing priority"