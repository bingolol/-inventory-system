"""Resources — 只读数据提供器 (URI 寻址)

agent 通过 URI 读取系统数据, 用于讲解、对账、自检。

阶段 1 提供 3 个 resource:
- accounting://policy/vat?ref_date=YYYY-MM-DD  增值税政策快照
- accounting://report/balance-sheet?date=YYYY-MM-DD  资产负债表 + trace
- accounting://ledger/accounts  会计科目表
"""
from datetime import datetime, date
from urllib.parse import urlparse, parse_qs
from typing import Any

from database import SessionLocal
from policy.vat_facts import load_vat_facts, PolicyExpiredError
from reports.engine import ReportEngine
from reports.definitions.balance_sheet import BALANCE_SHEET
from crud.finance._snapshot import LedgerSnapshot
from utils import end_of_day
import models_finance


def read_resource(uri: str) -> dict:
    """根据 URI 返回 resource 内容。

    URI 格式: accounting://<path>?<query>
    urlparse 会把 scheme 后第一段当作 netloc (如 accounting://policy/vat 中 netloc=policy, path=/vat),
    所以这里用 netloc + path 拼接得到完整路径。

    :raises ValueError: URI 不支持或参数缺失
    :raises PolicyExpiredError: 政策已到期
    """
    parsed = urlparse(uri)
    full_path = parsed.netloc + parsed.path
    query = parse_qs(parsed.query)

    if full_path == "policy/vat":
        return _read_vat_policy(query)
    elif full_path == "report/balance-sheet":
        return _read_balance_sheet(query)
    elif full_path == "report/income-statement":
        return _read_income_statement(query)
    elif full_path == "ledger/accounts":
        return _read_ledger_accounts()
    else:
        raise ValueError(f"不支持的 resource URI: {uri} (full_path={full_path})")


def _read_vat_policy(query: dict) -> dict:
    """增值税政策快照。"""
    ref_date_str = query.get("ref_date", [None])[0]
    ref_date = date.fromisoformat(ref_date_str) if ref_date_str else date.today()

    facts = load_vat_facts(ref_date)
    # legal_rates 的 value 是 PolicyFact 对象, 只取 .value
    legal_rates = {}
    for k, v in facts.legal_rates.items():
        legal_rates[k] = str(v.value) if hasattr(v, "value") else str(v)
    return {
        "ref_date": ref_date.isoformat(),
        "small_scale_syndicated_rate": str(facts.small_scale_syndicated_rate),
        "small_scale_reduced_rate": str(facts.small_scale_reduced_rate),
        "small_scale_quarterly_exemption": str(facts.small_scale_quarterly_exemption),
        "general_default_rate": str(facts.general_default_rate),
        "legal_rates": legal_rates,
        "note": "小规模纳税人 2023-2027 年减按 1% 征收; 季度销售额 ≤30 万普票免征。"
                "一般纳税人适用 13%/9%/6%/0% 税率。",
    }


def _read_balance_sheet(query: dict) -> dict:
    """资产负债表 (默认带 trace 追溯链)。"""
    from .account_context import require_account_id

    date_str = query.get("date", [None])[0]
    if not date_str:
        raise ValueError("balance-sheet resource 必须提供 date 参数 (YYYY-MM-DD)")

    account_id = require_account_id()
    qd = end_of_day(datetime.strptime(date_str, "%Y-%m-%d"))

    db = SessionLocal()
    try:
        sn = LedgerSnapshot(db, account_id, bs_cutoff=qd)
        engine = ReportEngine()
        result = engine.execute(BALANCE_SHEET, sn, trace=True, source_mode="invoice")
        return {
            "date": date_str,
            "account_id": account_id,
            "balance_sheet": result,
        }
    finally:
        db.close()


def _read_income_statement(query: dict) -> dict:
    """利润表 (默认带 trace 追溯链)。"""
    from .account_context import require_account_id
    from reports.definitions.income_statement import INCOME_STATEMENT

    start_str = query.get("start", [None])[0]
    end_str = query.get("end", [None])[0]
    if not start_str or not end_str:
        raise ValueError("income-statement resource 必须提供 start 和 end 参数 (YYYY-MM-DD)")

    account_id = require_account_id()
    sd = datetime.strptime(start_str, "%Y-%m-%d")
    ed = end_of_day(datetime.strptime(end_str, "%Y-%m-%d"))

    db = SessionLocal()
    try:
        sn = LedgerSnapshot(db, account_id, bs_cutoff=ed, period_start=sd, period_end=ed)
        engine = ReportEngine()
        result = engine.execute(INCOME_STATEMENT, sn, trace=True)
        return {
            "start_date": start_str,
            "end_date": end_str,
            "account_id": account_id,
            "income_statement": result,
        }
    finally:
        db.close()


def _read_ledger_accounts() -> dict:
    """会计科目表 (含 is_leaf 标志, 用于录入校验)。"""
    from .account_context import require_account_id

    account_id = require_account_id()
    db = SessionLocal()
    try:
        # 找到当前账本对应的 ledger (通过 Account.code 关联 Ledger.code)
        import models
        account = db.query(models.Account).filter(
            models.Account.id == account_id
        ).first()
        if not account:
            raise ValueError(f"账本 {account_id} 不存在")

        ledger = db.query(models_finance.Ledger).filter(
            models_finance.Ledger.code == account.code
        ).first()
        if not ledger:
            return {"account_id": account_id, "accounts": []}

        items = db.query(models_finance.LedgerAccount).filter(
            models_finance.LedgerAccount.ledger_id == ledger.id,
            models_finance.LedgerAccount.is_active == True,
        ).order_by(models_finance.LedgerAccount.code.asc()).all()

        return {
            "account_id": account_id,
            "ledger_code": ledger.code,
            "accounts": [
                {
                    "code": la.code,
                    "name": la.name,
                    "account_type": la.account_type,
                    "is_leaf": la.is_leaf,
                    "parent_id": la.parent_id,
                }
                for la in items
            ],
        }
    finally:
        db.close()


# Resource 清单 (供 server.py 注册)
RESOURCE_TEMPLATES = [
    {
        "uriTemplate": "accounting://policy/vat?ref_date={ref_date}",
        "name": "增值税政策快照",
        "description": (
            "返回指定日期有效的增值税政策 (税率、免征门槛、法规文号)。"
            "用于讲解增值税适用政策、判断小规模季度免征。"
        ),
        "mimeType": "application/json",
    },
    {
        "uriTemplate": "accounting://report/balance-sheet?date={date}",
        "name": "资产负债表 (含追溯链)",
        "description": (
            "返回指定日期的资产负债表, 字段附 contributions 追溯链。"
            "用于解释报表项目的来源 (凭证/发票/库存流水)。"
        ),
        "mimeType": "application/json",
    },
    {
        "uriTemplate": "accounting://report/income-statement?start={start}&end={end}",
        "name": "利润表 (含追溯链)",
        "description": (
            "返回指定期间的利润表, 字段附 contributions 追溯链。"
            "用于解释收入/成本/费用的构成来源。"
        ),
        "mimeType": "application/json",
    },
    {
        "uriTemplate": "accounting://ledger/accounts",
        "name": "会计科目表",
        "description": (
            "返回当前账本的会计科目表 (含 is_leaf 标志)。"
            "用于录入时校验科目编码、讲解科目层级。"
        ),
        "mimeType": "application/json",
    },
]
