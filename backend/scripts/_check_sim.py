"""验证全部阶段数据正确性 — 对照真实业务"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
import models
import models_finance
from decimal import Decimal
from utils.price import combine

db = SessionLocal()

def _sum_account(code):
    """计算科目借方累计-贷方累计"""
    la = db.query(models_finance.LedgerAccount).filter(
        models_finance.LedgerAccount.ledger_id == 1,
        models_finance.LedgerAccount.code == code,
    ).first()
    if not la:
        return Decimal("0")
    lines = db.query(models_finance.AccountMoveLine).filter(
        models_finance.AccountMoveLine.ledger_account_id == la.id
    ).all()
    debit = sum((l.debit_l2 or Decimal("0")) for l in lines)
    credit = sum((l.credit_l2 or Decimal("0")) for l in lines)
    return debit - credit

def _sum_account_dc(code):
    """返回 (借方累计, 贷方累计)"""
    la = db.query(models_finance.LedgerAccount).filter(
        models_finance.LedgerAccount.ledger_id == 1,
        models_finance.LedgerAccount.code == code,
    ).first()
    if not la:
        return Decimal("0"), Decimal("0")
    lines = db.query(models_finance.AccountMoveLine).filter(
        models_finance.AccountMoveLine.ledger_account_id == la.id
    ).all()
    debit = sum((l.debit_l2 or Decimal("0")) for l in lines)
    credit = sum((l.credit_l2 or Decimal("0")) for l in lines)
    return debit, credit

print("=" * 70)
print("1. 银行账户余额")
print("=" * 70)
ba = db.query(models.BankAccount).filter(models.BankAccount.id == 1).first()
print(f"  余额: {ba.balance_l4}")
# 预期: 0+0.01+2000-22.80-50-150+5000+1000+0.60+1800+1200+2400+1.23+1.23 = 13180.87

print("\n" + "=" * 70)
print("2. 销售单汇总（按月）")
print("=" * 70)
sos = db.query(models.SaleOrder).filter(
    models.SaleOrder.account_id == 1,
    models.SaleOrder.order_no.like("SO-%")
).all()
total_with_tax = Decimal("0")
total_tax = Decimal("0")
for s in sos:
    # 计算单张税额
    tax = sum(combine(si.total_price_l1, si.tax_rate_l1)[0] for si in s.items)
    print(f"  {s.order_no} 日期={s.sale_date_l1.date()} 含税={s.total_price_l1} 税额={tax}")
    total_with_tax += s.total_price_l1
    total_tax += tax
print(f"\n  合计: 含税={total_with_tax} 税额={total_tax}")

print("\n" + "=" * 70)
print("3. 关键科目余额")
print("=" * 70)
for code in ["1002", "1122", "1405", "1601", "2241", "6001",
             "6601", "6603", "222101", "222103", "222106", "4103"]:
    d, c = _sum_account_dc(code)
    la = db.query(models_finance.LedgerAccount).filter(
        models_finance.LedgerAccount.ledger_id == 1,
        models_finance.LedgerAccount.code == code,
    ).first()
    name = la.name if la else "?"
    print(f"  {code} {name}: 借={d} 贷={c} 余额(借-贷)={d-c}")

print("\n" + "=" * 70)
print("4. 银行余额对照")
print("=" * 70)
bank_calc = _sum_account("1002")
print(f"  BankAccount.balance_l4: {ba.balance_l4}")
print(f"  1002 总账余额: {bank_calc}")
print(f"  差异: {ba.balance_l4 - bank_calc}")

print("\n" + "=" * 70)
print("5. 个人垫付合计")
print("=" * 70)
pas = db.query(models.PersonalAdvance).filter(
    models.PersonalAdvance.account_id == 1
).all()
pa_total = sum(pa.amount_l1 for pa in pas)
print(f"  笔数: {len(pas)}")
print(f"  合计: {pa_total}")
print(f"  2241 余额: {_sum_account('2241')}")

print("\n" + "=" * 70)
print("6. 固定资产")
print("=" * 70)
fas = db.query(models.FixedAsset).filter(models.FixedAsset.account_id == 1).all()
fa_total = sum(fa.original_value_l1 for fa in fas)
for fa in fas:
    print(f"  {fa.asset_code} {fa.name} 原值={fa.original_value_l1} 购入={fa.start_date_l1}")
print(f"  合计原值: {fa_total}")
print(f"  1601 余额: {_sum_account('1601')}")

print("\n" + "=" * 70)
print("7. 季度销售税额（应交增值税 222103，仅模拟期间 2025-12-01 后）")
print("=" * 70)
# 只统计 2025-12-01 之后的 sale_order 凭证
from datetime import datetime as dt
cutoff = dt(2025, 12, 1)
ams = db.query(models_finance.AccountMove).filter(
    models_finance.AccountMove.source_model == "sale_order",
    models_finance.AccountMove.is_reversal == False,
    models_finance.AccountMove.date_l1 >= cutoff,
).all()
la_222103 = db.query(models_finance.LedgerAccount).filter(
    models_finance.LedgerAccount.ledger_id == 1,
    models_finance.LedgerAccount.code == "222103",
).first()
q_tax = {}
for m in ams:
    mls = db.query(models_finance.AccountMoveLine).filter(models_finance.AccountMoveLine.move_id == m.id).all()
    for line in mls:
        if line.ledger_account_id == la_222103.id and line.credit_l2 and line.credit_l2 > 0:
            year = m.date_l1.year
            q = (m.date_l1.month - 1) // 3 + 1
            key = (year, q)
            q_tax[key] = q_tax.get(key, Decimal("0")) + line.credit_l2
print(f"  2025 Q4 增值税: {q_tax.get((2025, 4), Decimal('0'))} (预期 19.80)")
print(f"  2026 Q1 增值税: {q_tax.get((2026, 1), Decimal('0'))} (预期 71.28)")
print(f"  2026 Q2 增值税: {q_tax.get((2026, 2), Decimal('0'))} (预期 41.58)")

print("\n" + "=" * 70)
print("8. 旧测试数据污染情况")
print("=" * 70)
# 统计 2025-12-01 前的凭证数量
old_ams = db.query(models_finance.AccountMove).filter(
    models_finance.AccountMove.date_l1 < cutoff
).count()
new_ams = db.query(models_finance.AccountMove).filter(
    models_finance.AccountMove.date_l1 >= cutoff
).count()
print(f"  2025-12-01 前凭证数: {old_ams}")
print(f"  2025-12-01 后凭证数: {new_ams}")
# 旧固定资产
old_fas = db.query(models.FixedAsset).filter(
    models.FixedAsset.start_date_l1 < cutoff
).count()
print(f"  旧固定资产数: {old_fas}")

print("\n" + "=" * 70)
print("8. 纳税人类型")
print("=" * 70)
acc = db.query(models.Account).filter(models.Account.id == 1).first()
print(f"  当前: {acc.taxpayer_type_l3}")

db.close()
