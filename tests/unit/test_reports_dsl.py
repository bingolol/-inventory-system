"""reports.dsl 类型系统测试 — P2 tracer bullet"""
import pytest
from decimal import Decimal

from reports.dsl import (
    Field, Source, Part, Check,
    Formula, Bucket,
    LEDGER_BALANCE, LEDGER_CREDIT, LEDGER_PERIOD, LEDGER_COMPOSITE,
    SUM_FIELDS, DualSource, STOCK_MOVES, OPENING, ESCAPE_HATCH,
    PositivePart, NegativePart, OpeningFallback, SubaccountFallback,
    INVOICE_TAX_NET,
)


def test_basic_field_creation():
    """最简单的字段定义语法"""
    f = Field(key="revenue", label="营业收入",
              source=LEDGER_COMPOSITE(parts=[
                  Part(codes=["6001", "6051"], side="credit", sign=+1),
                  Part(codes=["6001", "6051"], side="debit", sign=-1),
              ], bucket=Bucket.PNL_EXCLUDED))
    assert f.key == "revenue"
    assert f.label == "营业收入"
    assert f.source.formula == Formula.COMPOSITE
    assert len(f.source.parts) == 2
    assert f.source.parts[0].codes == ["6001", "6051"]


def test_ledger_balance():
    s = LEDGER_BALANCE(["1001", "1002"])
    assert s.formula == Formula.CUM_BALANCE
    assert s.codes == ["1001", "1002"]


def test_ledger_credit_with_bucket():
    s = LEDGER_CREDIT(["2202"], bucket=Bucket.PNL_EXCLUDED)
    assert s.formula == Formula.CUM_CREDIT
    assert s.bucket == Bucket.PNL_EXCLUDED


def test_ledger_period_default_bucket():
    s = LEDGER_PERIOD(["6401"])
    assert s.formula == Formula.PERIOD_NET
    assert s.bucket == Bucket.PNL_EXCLUDED


def test_sum_fields():
    s = SUM_FIELDS(["monetary_funds", "accounts_receivable"])
    assert s.formula == Formula.SUM_FIELDS
    assert s.deps == ["monetary_funds", "accounts_receivable"]


def test_dual_source():
    primary = INVOICE_TAX_NET()
    secondary = LEDGER_CREDIT(["222101", "222103", "222107"])
    s = DualSource(primary, secondary)
    assert s.primary.formula == Formula.INVOICE_TAX_NET
    assert s.secondary.formula == Formula.CUM_CREDIT


def test_transform_positive_part():
    f = Field(key="vat_payable_l1", label="应交增值税",
              source=SUM_FIELDS(["_vat_net"]),
              transform=PositivePart())
    assert f.transform.formula == Formula.POSITIVE_PART


def test_transform_negative_part_abs():
    f = Field(key="prepaid_tax", label="预付税款",
              source=SUM_FIELDS(["_vat_net"]),
              transform=NegativePart(abs=True))
    assert f.transform.formula == Formula.NEGATIVE_PART
    assert f.transform.abs is True


def test_transform_opening_fallback():
    f = Field(key="inventory", label="存货",
              source=STOCK_MOVES(),
              transform=OpeningFallback("inventory_value"))
    assert f.transform.formula == Formula.OPENING_FALLBACK
    assert f.transform.opening_key == "inventory_value"


def test_transform_subaccount_fallback():
    f = Field(key="tax_surcharges", label="税金及附加",
              source=LEDGER_PERIOD(["6403"]),
              transform=SubaccountFallback(["640302", "640303", "640304"]))
    assert f.transform.formula == Formula.SUBACCOUNT_FALLBACK
    assert len(f.transform.subaccount_codes) == 3


def test_escape_hatch():
    def my_resolver(snapshot):
        return Decimal("0"), []

    f = Field(key="ending_cash", label="库存现金",
              source=ESCAPE_HATCH(my_resolver))
    assert f.source.formula == Formula.ESCAPE_HATCH
    assert callable(f.source.resolver)


def test_check():
    c = Check(left=["total_assets"], op="==",
              right=["total_liabilities", "total_equity"],
              desc="资产 = 负债 + 权益")
    assert c.op == "=="
    assert c.left == ["total_assets"]


def test_field_roundtrip_deps_collection():
    """SUM_FIELDS 字段的依赖能正确收集"""
    fields = [
        Field("a", "A", source=LEDGER_BALANCE(["1001"])),
        Field("b", "B", source=LEDGER_CREDIT(["2202"])),
        Field("c", "C", source=SUM_FIELDS(["a", "b"])),
    ]
    assert fields[2].source.deps == ["a", "b"]


def test_bucket_values():
    assert Bucket.ALL.value == "all"
    assert Bucket.PNL_EXCLUDED.value == "pnl_excluded"
    assert Bucket.BUSINESS_ONLY.value == "business_only"
    assert Bucket.INTERNAL_ONLY.value == "internal_only"


def test_formula_values():
    """确认所有 Formula 值唯一且稳定"""
    values = {f.value for f in Formula}
    assert len(values) == len(Formula), "Formula 值应唯一"


def test_opening_source():
    s = OPENING("cash_balance")
    assert s.formula == Formula.OPENING
    assert s.key == "cash_balance"
