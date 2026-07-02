"""财务引擎集成层 — 带防御性检查的 JournalEngine 封装

所有业务入口通过此模块调用会计引擎，而不是直接调用 JournalEngine。
"""
from decimal import Decimal
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from crud.base import get_account
from accounting_engine import AccountingError
from models_finance import (
    Ledger, LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine,
)
from engine_journal import JournalEngine
from errors import BusinessError, ErrorCode
from utils import Q2
from lineage import writes, reads, TIER_L3
from rules import enforce_rules


EXPENSE_ACCOUNT_CODE_MAP = {
    "销售费用": "6602",
    "管理费用": "6601",
    "财务费用": "6603",
}


CHART_OF_ACCOUNTS = [
    # 资产类
    ("1001", "库存现金", "asset"),
    ("1002", "银行存款", "asset"),
    ("1122", "应收账款", "asset_receivable"),
    ("1123", "预付账款", "asset_prepaid"),
    ("1221", "其他应收款", "asset"),
    ("1405", "库存商品", "asset"),
    ("1601", "固定资产", "asset"),
    ("1602", "累计折旧", "asset_contra"),
    ("1701", "无形资产", "asset"),
    ("1702", "累计摊销", "asset_contra"),
    ("1901", "待处理财产损溢", "asset"),  # 盘盈盘亏中转科目（修复 #8）
    # 负债类
    ("2001", "短期借款", "liability"),
    ("2202", "应付账款", "liability_payable"),
    ("2203", "预收账款", "liability_advance"),
    ("2211", "应付职工薪酬", "liability"),
    ("2221", "应交税费", "liability"),
    ("222101", "应交增值税-销项税额", "liability"),
    ("222102", "应交增值税-进项税额", "liability"),
    ("222103", "应交增值税-小规模", "liability"),
    ("222106", "应交增值税-转出未交增值税", "liability"),
    ("222107", "未交增值税", "liability"),
    ("222104", "应交附加税", "liability"),
    ("222105", "应交所得税", "liability"),
    ("222108", "应交个人所得税", "liability"),  # 代扣员工个税(业务因果链 E)
    ("222110", "应交城市维护建设税", "liability"),
    ("222111", "应交教育费附加", "liability"),
    ("222112", "应交地方教育附加", "liability"),
    ("222113", "应交消费税", "liability"),
    ("222114", "应交资源税", "liability"),
    ("222115", "应交土地增值税", "liability"),
    ("222116", "应交房产税", "liability"),
    ("222117", "应交城镇土地使用税", "liability"),
    ("222118", "应交车船税", "liability"),
    ("222119", "应交印花税", "liability"),
    ("222120", "应交环境保护税", "liability"),
    ("2241", "其他应付款", "liability"),
    ("2501", "长期借款", "liability"),
    # 权益类
    ("3001", "实收资本", "equity"),
    ("4001", "资本公积", "equity"),
    ("4101", "盈余公积", "equity"),
    ("4103", "本年利润", "equity"),
    ("4104", "利润分配", "equity"),
    # 损益类
    ("6001", "主营业务收入", "income"),
    ("6051", "其他业务收入", "income"),
    ("6111", "资产处置收益", "income"),
    ("6401", "主营业务成本", "expense"),
    ("6403", "税金及附加", "expense"),
    ("640301", "税金及附加-消费税", "expense"),
    ("640302", "税金及附加-城市维护建设税", "expense"),
    ("640303", "税金及附加-教育费附加", "expense"),
    ("640304", "税金及附加-地方教育附加", "expense"),
    ("640305", "税金及附加-资源税", "expense"),
    ("640306", "税金及附加-土地增值税", "expense"),
    ("640307", "税金及附加-房产税", "expense"),
    ("640308", "税金及附加-城镇土地使用税", "expense"),
    ("640309", "税金及附加-车船税", "expense"),
    ("640310", "税金及附加-印花税", "expense"),
    ("640311", "税金及附加-环境保护税", "expense"),
    ("6601", "管理费用", "expense"),
    ("6602", "销售费用", "expense"),
    ("6603", "财务费用", "expense"),
    ("6701", "营业外支出", "expense"),
    ("6301", "营业外收入-税收减免", "income"),  # 增值税减免转入（财税〔2008〕151号）
    ("6711", "资产处置损失", "expense"),
    ("6801", "所得税费用", "expense"),
]


@reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
@writes("Ledger.taxpayer_type_l3", tier=TIER_L3, source="policy")
def get_or_create_ledger_id(db: Session, account_id: int) -> int:
    """获取 account_id 对应的 ledger_id，不存在则自动创建"""
    account = get_account(db, account_id)
    if not account:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"账本不存在: account_id={account_id}",
        )
    ledger = db.query(Ledger).filter(Ledger.code == account.code).first()
    if not ledger:
        ledger = Ledger(
            name=account.name,
            type=account.type or "company",
            code=account.code,
            taxpayer_type_l3=account.taxpayer_type_l3 or "small_scale",
        )
        db.add(ledger)
        db.flush()
        for code, name, atype in CHART_OF_ACCOUNTS:
            la = LedgerAccount(ledger_id=ledger.id, code=code, name=name, account_type=atype, is_leaf=True)
            db.add(la)
            db.flush()
            db.add(LedgerAccountBalance(ledger_account_id=la.id, balance_l4=0, debit_total_l4=0, credit_total_l4=0))
    else:
        # 如果 ledger 已存在但缺少 LedgerAccount，自动补齐（科目表扩展后同步）
        existing_codes = {la.code for la in db.query(LedgerAccount.code).filter(LedgerAccount.ledger_id == ledger.id)}
        for code, name, atype in CHART_OF_ACCOUNTS:
            if code not in existing_codes:
                la = LedgerAccount(ledger_id=ledger.id, code=code, name=name, account_type=atype, is_leaf=True)
                db.add(la)
                db.flush()
                db.add(LedgerAccountBalance(ledger_account_id=la.id, balance_l4=0, debit_total_l4=0, credit_total_l4=0))
    return ledger.id


get_ledger_id = get_or_create_ledger_id  # 向下兼容


def _calc_tax_from_items(total_with_tax: Decimal, items: list) -> dict:
    """从 items 逐行计算税额，Decimal + quantize 精度保护

    items 每个元素需包含: total_price (含税小计), tax_rate
    返回: {"tax_amount": Decimal, "total_without_tax": Decimal}
    """
    tax_amount = Decimal("0")
    for item in items:
        tp = Decimal(str(item["total_price"]))
        rate = Decimal(str(item["tax_rate"]))
        line_tax = (tp * rate / (Decimal("1") + rate)).quantize(Q2)
        tax_amount += line_tax
    tax_amount = tax_amount.quantize(Q2)
    total_without_tax = (Decimal(str(total_with_tax)) - tax_amount).quantize(Q2)
    return {"tax_amount": tax_amount, "total_without_tax": total_without_tax}


def post_journal(
    db: Session,
    account_id: int,
    move_type: str,
    source: dict,
    force: bool = False,
) -> AccountMove:
    """过账（带重复过账防御）

    若相同 source_model + source_id 且非冲红的凭证已存在，直接返回旧凭证。
    force=True 时跳过此防御，用于冲红后重建凭证（如订单明细更新、状态恢复）。
    会计错误转为 BusinessError 保证事务回滚。
    """
    sm = source.get("source_model")
    si = source.get("source_id")
    if sm and si is not None and not force:
        ledger_id = get_or_create_ledger_id(db, account_id)
        existing = db.query(AccountMove).filter(
            AccountMove.ledger_id == ledger_id,
            AccountMove.source_model == sm,
            AccountMove.source_id == si,
            AccountMove.is_reversal == False,
        ).first()
        if existing:
            return existing

    ledger_id = get_or_create_ledger_id(db, account_id)
    try:
        engine = JournalEngine(db)
        return engine.post(ledger_id, move_type, source)
    except AccountingError as e:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=e.message,
            data={"accounting_code": e.code},
        )


def reverse_journal(
    db: Session,
    account_id: int,
    source_model: str,
    source_id: int,
    reversal_date: Optional[date] = None,
    force: bool = False,
) -> Optional[AccountMove]:
    """冲红原凭证（带幂等防御）

    查找相同 source_model + source_id 的原凭证，借贷互换生成冲红凭证。
    已冲红过 → 返回 None；无原凭证 → 返回 None。

    force=True 时跳过幂等检查，并取最近一条 is_reversal=False 的凭证作为冲红基准
    （用于"冲红+重建"反复执行的场景：同一 source_id 有多条正向凭证，需冲红最近一条）。
    """
    existing_reversal = db.query(AccountMove).filter(
        AccountMove.source_model == source_model,
        AccountMove.source_id == source_id,
        AccountMove.is_reversal == True,
    ).first()
    if existing_reversal and not force:
        return None

    orig_query = db.query(AccountMove).filter(
        AccountMove.source_model == source_model,
        AccountMove.source_id == source_id,
        AccountMove.is_reversal == False,
    )
    if force:
        original = orig_query.order_by(AccountMove.id.desc()).first()
    else:
        original = orig_query.first()
    if not original:
        return None

    engine = JournalEngine(db)

    # BR-22: 默认用原凭证日期作为冲红日期，与 InventoryEngine.reverse 的 StockMove
    # 反向流水 move_date（也是从原单据取业务日期）保持一致。否则 BS 报表按 cutoff
    # 过滤时，StockMove 反向流水会进表但 AccountMove 反向凭证不会进表，
    # 造成"库存值包含冲回、利润不含冲回"的资产与权益错配（典型 diff=40000 不平）。
    reversal = AccountMove(
        ledger_id=original.ledger_id,
        name=f"冲红-{original.name}",
        move_type=original.move_type,
        date_l1=reversal_date or original.date_l1,
        state="posted",
        source_model=source_model,
        source_id=source_id,
        amount_total_l2=original.amount_total_l2,
        reversed_entry_id=original.id,
        is_reversal=True,
    )
    db.add(reversal)
    db.flush()

    for ol in original.line_ids:
        rl = AccountMoveLine(
            move_id=reversal.id,
            ledger_account_id=ol.ledger_account_id,
            debit_l2=ol.credit_l2,
            credit_l2=ol.debit_l2,
            partner_id=ol.partner_id,
            partner_type=ol.partner_type,
            amount_residual_l2=ol.credit_l2 or ol.debit_l2,
        )
        db.add(rl)
        db.flush()
        engine.ledger_engine.update_balance(rl)

    # AS-01 借贷平衡校验：冲红凭证生成后必须保持借方=贷方
    enforce_rules(db, ["AS-01"], {"move_id": reversal.id})

    return reversal
