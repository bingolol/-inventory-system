"""现金流量表"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

import models
from enums import FlowCategory
from utils import _d, Q2, end_of_day
from errors import BusinessError, ErrorCode
from lineage import reads, TIER_L1, TIER_L2, TIER_L4

from ._snapshot import LedgerSnapshot
from .opening_balances import get_latest_opening_balance
from .cash_flow_classifier import (
    classify_bank_transaction,
    classify_cash_flow_transaction,
    CF_LINE_MAP,
)

@reads("CashFlowTransaction.flow_category_l2", tier=TIER_L2, source="engine")
def list_cash_flow_transactions(db: Session, account_id: int, skip: int = 0, limit: int = 100,
                                 start_date: str = None, end_date: str = None, flow_category: str = None):
    q = db.query(models.CashFlowTransaction).filter(models.CashFlowTransaction.account_id == account_id)
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        q = q.filter(models.CashFlowTransaction.transaction_date_l1 >= start_dt)
    if end_date:
        end_dt = end_of_day(datetime.strptime(end_date, "%Y-%m-%d"))
        q = q.filter(models.CashFlowTransaction.transaction_date_l1 <= end_dt)
    if flow_category:
        q = q.filter(models.CashFlowTransaction.flow_category_l2 == flow_category)
    total = q.count()
    items = q.order_by(models.CashFlowTransaction.transaction_date_l1.desc()).offset(skip).limit(limit).all()
    return total, items


@reads("OpeningBalance.cash_balance_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.bank_balance_l1", tier=TIER_L1, source="external")
@reads("CashFlowTransaction.amount_l2", tier=TIER_L2, source="engine")
@reads("BankTransaction.amount_l2", tier=TIER_L2, source="engine")
def generate_cash_flow_statement(db: Session, account_id: int, start_date: str, end_date: str):
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    sn = LedgerSnapshot(db, account_id, period_start=start_dt, period_end=end_dt)

    opening_balance = get_latest_opening_balance(db, account_id, start_date)
    beginning_cash_balance = (_d(opening_balance.cash_balance_l1) + _d(opening_balance.bank_balance_l1)) if opening_balance else Decimal('0')

    # 初始化 CF01~CF19 明细金额（收为正，付为负）
    cf_items = {code: Decimal("0") for code in CF_LINE_MAP.keys()}

    # 手动录入的现金流水
    for tx in sn.cash_flow_transactions():
        code = classify_cash_flow_transaction(tx)
        sign = Decimal("1") if tx.type == "inflow" else Decimal("-1")
        cf_items[code] += sign * _d(tx.amount_l2)

    # 从银行流水表读取数据
    for tx in sn.bank_transactions():
        code = classify_bank_transaction(db, tx)
        sign = Decimal("1") if tx.transaction_type == "inflow" else Decimal("-1")
        cf_items[code] += sign * _d(tx.amount_l2)

    # 按大类汇总
    operating_inflows = cf_items.get("CF01", Decimal("0")) + cf_items.get("CF02", Decimal("0"))
    operating_outflows = -(cf_items.get("CF03", Decimal("0")) + cf_items.get("CF04", Decimal("0"))
                          + cf_items.get("CF05", Decimal("0")) + cf_items.get("CF06", Decimal("0")))
    investing_inflows = cf_items.get("CF08", Decimal("0")) + cf_items.get("CF09", Decimal("0")) + cf_items.get("CF10", Decimal("0"))
    investing_outflows = -(cf_items.get("CF11", Decimal("0")) + cf_items.get("CF12", Decimal("0")))
    financing_inflows = cf_items.get("CF14", Decimal("0")) + cf_items.get("CF15", Decimal("0"))
    financing_outflows = -(cf_items.get("CF16", Decimal("0")) + cf_items.get("CF17", Decimal("0")) + cf_items.get("CF18", Decimal("0")))

    net_operating = operating_inflows - operating_outflows
    net_investing = investing_inflows - investing_outflows
    net_financing = financing_inflows - financing_outflows
    net_cash_flow = net_operating + net_investing + net_financing
    ending_cash_balance = beginning_cash_balance + net_cash_flow

    # ── 余额校验 ──
    expected_ending_balance = beginning_cash_balance + net_cash_flow
    if abs(ending_cash_balance - expected_ending_balance) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.CASH_FLOW_STATEMENT_INVALID,
            message=f"现金流量表公式错误：期末余额 {ending_cash_balance} ≠ 期初余额 {beginning_cash_balance} + 净现金流量 {net_cash_flow}",
            data={"ending_cash_balance": float(ending_cash_balance), "beginning_cash_balance": float(beginning_cash_balance), "net_cash_flow": float(net_cash_flow)}
        )

    expected_net_cash_flow = net_operating + net_investing + net_financing
    if abs(net_cash_flow - expected_net_cash_flow) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.CASH_FLOW_STATEMENT_INVALID,
            message=f"现金流量表公式错误：净现金流量 {net_cash_flow} ≠ 经营活动净额 {net_operating} + 投资活动净额 {net_investing} + 筹资活动净额 {net_financing}",
            data={"net_cash_flow": float(net_cash_flow), "net_operating": float(net_operating), "net_investing": float(net_investing), "net_financing": float(net_financing)}
        )

    cf_details = {code: amount.quantize(Q2) for code, amount in cf_items.items()}

    return {
        "period": f"{start_date} 至 {end_date}",
        "operating_activities": {
            "inflows": operating_inflows.quantize(Q2),
            "outflows": operating_outflows.quantize(Q2),
            "net": net_operating.quantize(Q2)
        },
        "investing_activities": {
            "inflows": investing_inflows.quantize(Q2),
            "outflows": investing_outflows.quantize(Q2),
            "net": net_investing.quantize(Q2)
        },
        "financing_activities": {
            "inflows": financing_inflows.quantize(Q2),
            "outflows": financing_outflows.quantize(Q2),
            "net": net_financing.quantize(Q2)
        },
        "net_cash_flow": net_cash_flow.quantize(Q2),
        "beginning_cash_balance": beginning_cash_balance.quantize(Q2),
        "ending_cash_balance": ending_cash_balance.quantize(Q2),
        "cf_details": cf_details,
    }
