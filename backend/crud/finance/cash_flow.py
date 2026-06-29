"""现金流量表"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

import models
from enums import FlowCategory
from utils import _d, Q2
from errors import BusinessError, ErrorCode

from .opening_balances import get_latest_opening_balance

def list_cash_flow_transactions(db: Session, account_id: int, skip: int = 0, limit: int = 100,
                                 start_date: str = None, end_date: str = None, flow_category: str = None):
    q = db.query(models.CashFlowTransaction).filter(models.CashFlowTransaction.account_id == account_id)
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        q = q.filter(models.CashFlowTransaction.transaction_date >= start_dt)
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        q = q.filter(models.CashFlowTransaction.transaction_date <= end_dt)
    if flow_category:
        q = q.filter(models.CashFlowTransaction.flow_category == flow_category)
    total = q.count()
    items = q.order_by(models.CashFlowTransaction.transaction_date.desc()).offset(skip).limit(limit).all()
    return total, items


def generate_cash_flow_statement(db: Session, account_id: int, start_date: str, end_date: str):
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    opening_balance = get_latest_opening_balance(db, account_id, start_date)
    beginning_cash_balance = (_d(opening_balance.cash_balance) + _d(opening_balance.bank_balance)) if opening_balance else Decimal('0')

    # ── 经营活动（只从银行流水读取，避免双重计算）──
    operating_inflows = Decimal('0')
    operating_outflows = Decimal('0')

    # 投资活动
    investing_inflows = Decimal('0')
    investing_outflows = Decimal('0')

    # 筹资活动
    financing_inflows = Decimal('0')
    financing_outflows = Decimal('0')

    # 手动录入的现金流水（用于投资/筹资活动）
    cash_transactions = db.query(models.CashFlowTransaction).filter(
        models.CashFlowTransaction.account_id == account_id,
        models.CashFlowTransaction.transaction_date >= start_dt,
        models.CashFlowTransaction.transaction_date <= end_dt
    ).all()

    for tx in cash_transactions:
        if tx.type == "inflow":
            if tx.flow_category == FlowCategory.INVESTING:
                investing_inflows += _d(tx.amount)
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_inflows += _d(tx.amount)
        else:
            if tx.flow_category == FlowCategory.INVESTING:
                investing_outflows += _d(tx.amount)
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_outflows += _d(tx.amount)

    # 从银行流水表读取数据（按 flow_category 分类）
    bank_transactions = db.query(models.BankTransaction).filter(
        models.BankTransaction.account_id == account_id,
        models.BankTransaction.transaction_date >= start_dt,
        models.BankTransaction.transaction_date <= end_dt
    ).all()

    for tx in bank_transactions:
        amount = _d(tx.amount)
        if tx.transaction_type == "inflow":
            if tx.flow_category == FlowCategory.INVESTING:
                investing_inflows += amount
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_inflows += amount
            else:
                operating_inflows += amount
        else:
            if tx.flow_category == FlowCategory.INVESTING:
                investing_outflows += amount
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_outflows += amount
            else:
                operating_outflows += amount

    net_operating = operating_inflows - operating_outflows
    net_investing = investing_inflows - investing_outflows
    net_financing = financing_inflows - financing_outflows
    net_cash_flow = net_operating + net_investing + net_financing
    ending_cash_balance = beginning_cash_balance + net_cash_flow

    # ── 余额校验 ──
    # 校验：期末余额 = 期初余额 + 净现金流量
    expected_ending_balance = beginning_cash_balance + net_cash_flow
    if abs(ending_cash_balance - expected_ending_balance) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.CASH_FLOW_STATEMENT_INVALID,
            message=f"现金流量表公式错误：期末余额 {ending_cash_balance} ≠ 期初余额 {beginning_cash_balance} + 净现金流量 {net_cash_flow}",
            data={"ending_cash_balance": float(ending_cash_balance), "beginning_cash_balance": float(beginning_cash_balance), "net_cash_flow": float(net_cash_flow)}
        )

    # 校验：净现金流量 = 经营活动净额 + 投资活动净额 + 筹资活动净额
    expected_net_cash_flow = net_operating + net_investing + net_financing
    if abs(net_cash_flow - expected_net_cash_flow) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.CASH_FLOW_STATEMENT_INVALID,
            message=f"现金流量表公式错误：净现金流量 {net_cash_flow} ≠ 经营活动净额 {net_operating} + 投资活动净额 {net_investing} + 筹资活动净额 {net_financing}",
            data={"net_cash_flow": float(net_cash_flow), "net_operating": float(net_operating), "net_investing": float(net_investing), "net_financing": float(net_financing)}
        )

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
        "ending_cash_balance": ending_cash_balance.quantize(Q2)
    }
