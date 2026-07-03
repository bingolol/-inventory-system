"""银行引擎 — BankTransaction 与 BankAccount.balance_l4 的唯一写入入口

BankTransaction 创建必须经 BankEngine.record_transaction()，禁止业务代码直接 new。
BankAccount.balance_l4 仅为缓存，财务真相源在 LedgerAccountBalance（科目 1002）。
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from models import BankAccount, BankTransaction
from errors import BusinessError, ErrorCode
from utils import _d
from lineage import writes, derives, TIER_L1, TIER_L2, TIER_L4


class BankEngine:
    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id

    @writes("BankTransaction.amount_l2", tier=TIER_L2, source="engine")
    @writes("BankTransaction.flow_category_l2", tier=TIER_L2, source="engine")
    @writes("BankTransaction.cash_flow_item_code_l2", tier=TIER_L2, source="engine")
    @writes("BankTransaction.transaction_date_l1", tier=TIER_L1, source="external")
    @derives("BankTransaction.balance_after_l4", from_fields=["BankTransaction.amount_l2"])
    @derives("BankAccount.balance_l4", from_fields=["BankTransaction.amount_l2"])
    def record_transaction(
        self,
        bank_account_id: int,
        transaction_type: str,
        amount: Decimal,
        transaction_date: datetime,
        description: str = "",
        reference_no: str = "",
        flow_category: str = "operating",
        cash_flow_item_code: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        allow_overdraft: bool = False,
    ) -> BankTransaction:
        """银行流水唯一创建入口（含余额同步与透支校验）

        统一处理：
        1. 银行账户行锁（防并发）
        2. 余额计算与透支校验（红冲场景 allow_overdraft=True 跳过）
        3. BankTransaction 写入（真相源）
        4. BankAccount.balance_l4 同步（缓存派生）

        Args:
            transaction_type: "inflow" / "outflow"
            amount: 交易金额（正数）
            transaction_date: 业务日期
            flow_category: operating / investing / financing
            cash_flow_item_code: 现金流量表项目代码 CF01~CF19
            related_entity_type: payment / receipt / personal_advance_repayment /
                                 fixed_asset_disposal / reversal / bank_entry
            related_entity_id: 关联实体 ID
            allow_overdraft: 红冲场景允许透支（跨期资金回滚可能短期负值）

        返回: BankTransaction（已 flush，可读 .id）
        """
        bank_account = self.db.query(BankAccount).filter(
            BankAccount.id == bank_account_id,
            BankAccount.account_id == self.account_id,
        ).with_for_update().first()
        if not bank_account:
            raise BusinessError(
                code=ErrorCode.BANK_ACCOUNT_NOT_FOUND,
                data={"bank_account_id": bank_account_id},
            )

        amount = _d(amount)
        if transaction_type == "inflow":
            new_balance = _d(bank_account.balance_l4) + amount
        else:
            new_balance = _d(bank_account.balance_l4) - amount
            if new_balance < 0 and not allow_overdraft:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=(
                        f"银行账户余额不足: 当前余额 {bank_account.balance_l4}，"
                        f"支出金额 {amount}，超额 {abs(new_balance)}"
                    ),
                    ai_instruction=(
                        f"STOP_RETRYING. 银行账户 {bank_account.bank_name} 余额仅 "
                        f"{bank_account.balance_l4}，不足以支出 {amount}。"
                        f"请减少金额或先充值。"
                    ),
                )

        tx = BankTransaction(
            account_id=self.account_id,
            bank_account_id=bank_account_id,
            transaction_type=transaction_type,
            amount_l2=amount,
            balance_after_l4=new_balance,
            transaction_date_l1=transaction_date,
            description=description,
            reference_no=reference_no,
            flow_category_l2=flow_category,
            cash_flow_item_code_l2=cash_flow_item_code,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
        self.db.add(tx)
        self.db.flush()
        bank_account.balance_l4 = new_balance
        return tx
