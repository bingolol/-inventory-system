"""现金流量表项目自动分类器

将 BankTransaction / CashFlowTransaction 按税务申报模板（会小企03表）的
22 个项目分类为 CF01~CF19（CF20~CF22 为计算项，无需取数）。
"""

from decimal import Decimal
from sqlalchemy.orm import Session

import models
from enums import FlowCategory

# 现金流量表项目代码 -> 申报模板行次
CF_LINE_MAP = {
    "CF01": 1,   # 销售产成品、商品、提供劳务收到的现金
    "CF02": 2,   # 收到其他与经营活动有关的现金
    "CF03": 3,   # 购买原材料、商品、接受劳务支付的现金
    "CF04": 4,   # 支付的职工薪酬
    "CF05": 5,   # 支付的税费
    "CF06": 6,   # 支付其他与经营活动有关的现金
    # CF07 经营活动产生的现金流量净额（计算）
    "CF08": 8,   # 收回短期投资、长期债券投资和长期股权投资收到的现金
    "CF09": 9,   # 取得投资收益收到的现金
    "CF10": 10,  # 处置固定资产、无形资产和其他非流动资产收回的现金净额
    "CF11": 11,  # 短期投资、长期债券投资和长期股权投资支付的现金
    "CF12": 12,  # 购建固定资产、无形资产和其他非流动资产支付的现金
    # CF13 投资活动产生的现金流量净额（计算）
    "CF14": 14,  # 取得借款收到的现金
    "CF15": 15,  # 吸收投资者投资收到的现金
    "CF16": 16,  # 偿还借款本金支付的现金
    "CF17": 17,  # 偿还借款利息支付的现金
    "CF18": 18,  # 分配利润支付的现金
    # CF19 筹资活动产生的现金流量净额（计算）
}


def _is_reversal_tx(tx):
    """判断是否为冲红流水"""
    desc = (tx.description or "").lower()
    return getattr(tx, "is_reversed", False) or "冲红" in desc or "reverse" in desc


def classify_bank_transaction(db: Session, tx) -> str:
    """根据 BankTransaction 的关联实体和描述返回 CF 项目代码"""
    # 若已手工指定，直接复用
    if tx.cash_flow_item_code_l2:
        return tx.cash_flow_item_code_l2

    transaction_type = getattr(tx, "transaction_type", None) or getattr(tx, "type", "outflow")
    is_inflow = transaction_type == "inflow"

    related_type = tx.related_entity_type
    related_id = tx.related_entity_id

    # 优先根据关联实体类型判断
    if related_type == "payment" and related_id:
        payment = db.query(models.Payment).filter(
            models.Payment.id == related_id,
            models.Payment.account_id == tx.account_id,
        ).first()
        if payment:
            ptype = payment.payment_type
            if ptype == "purchase":
                return "CF03"
            if ptype == "salary":
                return "CF04"
            if ptype == "tax":
                return "CF05"
            # expense / other 归为其他经营活动付现
            return "CF06"

    if related_type == "receipt" and related_id:
        receipt = db.query(models.Receipt).filter(
            models.Receipt.id == related_id,
            models.Receipt.account_id == tx.account_id,
        ).first()
        if receipt:
            rtype = receipt.receipt_type
            if rtype == "sale":
                return "CF01"
            return "CF02"

    if related_type == "fixed_asset":
        return "CF12" if not is_inflow else "CF10"

    if related_type in ("personal_advance", "personal_advance_repayment"):
        # 个人垫付/还款属于经营活动其他
        return "CF02" if is_inflow else "CF06"

    # 根据原始 flow_category 兜底
    category = tx.flow_category_l2 or FlowCategory.OPERATING
    if category == FlowCategory.INVESTING:
        if is_inflow:
            return "CF08"  # 投资收回（无法细分时统归入此）
        return "CF12"      # 投资支付（无法细分时统归入此）
    if category == FlowCategory.FINANCING:
        if is_inflow:
            return "CF14"  # 借款收到（无法细分时统归入此）
        return "CF16"      # 偿还本金（无法细分时统归入此）

    # 经营活动中无法识别的流水：利息收入/手续费等
    desc = (tx.description or "").lower()
    if is_inflow:
        if "利息" in desc:
            return "CF02"  # 银行利息收入放经营其他
        return "CF01" if ("销售" in desc or "货款" in desc or "收入" in desc) else "CF02"
    else:
        if "税费" in desc or "税款" in desc:
            return "CF05"
        if "工资" in desc or "薪" in desc:
            return "CF04"
        if "采购" in desc or "货款" in desc:
            return "CF03"
        return "CF06"


def classify_cash_flow_transaction(tx) -> str:
    """手动录入的 CashFlowTransaction 分类"""
    if tx.cash_flow_item_code_l2:
        return tx.cash_flow_item_code_l2

    is_inflow = tx.type == "inflow"
    category = tx.flow_category_l2 or FlowCategory.OPERATING

    if category == FlowCategory.INVESTING:
        return "CF08" if is_inflow else "CF12"
    if category == FlowCategory.FINANCING:
        return "CF14" if is_inflow else "CF16"

    desc = (tx.description or "").lower()
    if is_inflow:
        if "销售" in desc or "货款" in desc:
            return "CF01"
        return "CF02"
    else:
        if "工资" in desc or "薪" in desc:
            return "CF04"
        if "税" in desc:
            return "CF05"
        if "采购" in desc or "货款" in desc:
            return "CF03"
        return "CF06"
