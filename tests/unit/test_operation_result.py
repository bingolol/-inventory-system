"""OperationResult 测试 - TDD 循环

Behavior 1: 创建 OperationResult 数据类
Behavior 2: 创建费用返回 OperationResult
Behavior 3: 创建采购单返回 OperationResult
Behavior 4: 创建销售单返回 OperationResult
"""

import sys
import os
import pytest
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from operation_result import OperationResult, EntityType, OperationType


# ═══════════════════════════════════════════════════════════
# Behavior 1: 创建 OperationResult 数据类（Critical）
# ═══════════════════════════════════════════════════════════

def test_operation_result_create():
    """创建 OperationResult 实例"""
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.EXPENSE,
        entity_id=123,
        summary="费用创建成功，金额 5000.00",
        ai_hint="费用已创建，状态为未付款。如需付款，请调用 POST /api/payments。",
        data={"id": 123, "amount": 5000.00}
    )
    
    assert result.success is True
    assert result.operation == OperationType.CREATE
    assert result.entity_type == EntityType.EXPENSE
    assert result.entity_id == 123
    assert result.summary == "费用创建成功，金额 5000.00"
    assert result.ai_hint == "费用已创建，状态为未付款。如需付款，请调用 POST /api/payments。"
    assert result.data["id"] == 123


def test_operation_result_to_dict():
    """OperationResult 序列化为字典"""
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.EXPENSE,
        entity_id=123,
        summary="费用创建成功，金额 5000.00",
        ai_hint="费用已创建，状态为未付款。如需付款，请调用 POST /api/payments。",
        data={"id": 123, "amount": 5000.00},
        changes={"payable": {"amount": "+5000.00"}}
    )
    
    d = result.to_dict()
    assert d["success"] is True
    assert d["operation"] == "create"
    assert d["entity_type"] == "expense"
    assert d["entity_id"] == 123
    assert d["summary"] == "费用创建成功，金额 5000.00"
    assert d["changes"]["payable"]["amount"] == "+5000.00"
    assert d["ai_hint"] == "费用已创建，状态为未付款。如需付款，请调用 POST /api/payments。"
    assert d["data"]["id"] == 123


def test_operation_result_with_decimal():
    """OperationResult 包含 Decimal 类型，序列化时应转为 float"""
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.PURCHASE_ORDER,
        entity_id=456,
        summary="采购单创建成功，金额 10000.00",
        ai_hint="采购单已创建。",
        data={"id": 456, "total_price": Decimal("10000.00")},
        changes={"payable": {"amount": Decimal("+10000.00")}}
    )
    
    d = result.to_dict()
    assert d["data"]["total_price"] == 10000.0
    assert d["changes"]["payable"]["amount"] == 10000.0
