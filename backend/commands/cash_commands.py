"""现金流相关 Command + Handler

费用(Expense)、付款(Payment)、收款(Receipt) 的写操作统一下沉到本模块，
routers 只负责解析请求并 dispatch。后续业务规则校验只需在 Handler 处注入。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from commands.base import Command, CommandHandler, register
from crud.base import log_op
from crud.invoice_linkage import has_invoice as linkage_has_invoice
from commands.reversal_ops import reverse_single_payment, reverse_single_receipt
from engine_bank import BankEngine
from enums import EXPENSE_CATEGORIES
from errors import BusinessError, ErrorCode
from finance_integration import post_journal, reverse_journal, EXPENSE_ACCOUNT_CODE_MAP
from image_utils import delete_old_image
from lineage import writes, TIER_L1, TIER_L2
from models import BankAccount, Expense, Payment, PurchaseOrder, Receipt, SaleOrder
from operation_result import EntityType, OperationResult, OperationType
from schemas import ExpenseCreate, ExpenseUpdate
from schemas.payment import PaymentCreate, PaymentOut
from schemas.receipt import ReceiptCreate, ReceiptOut
from utils import to_decimal

Q2 = Decimal("0.01")


# ═══════════════════════════════════════════════════════════
# Expense Commands
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateExpense(Command):
    expense: Optional[ExpenseCreate] = None


@register(CreateExpense)
class CreateExpenseHandler(CommandHandler):
    @writes("Expense.amount_l1", tier=TIER_L1, source="external")
    @writes("Expense.expense_date_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: CreateExpense, db: Any) -> Any:
        account_id = cmd.account_id
        expense = cmd.expense

        if expense.category not in EXPENSE_CATEGORIES:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                data={"details": f"费用类别 '{expense.category}' 不合法，合法值: {EXPENSE_CATEGORIES}"},
            )

        db_expense = Expense(
            account_id=account_id,
            category=expense.category,
            functional_category=expense.functional_category or "管理费用",
            amount_l1=expense.amount,
            expense_date_l1=expense.expense_date,
            payment_method=expense.payment_method,
            payment_status="unpaid",
            description=expense.description,
            image_url=expense.image_url or "",
        )
        db.add(db_expense)
        db.flush()

        expense_code = EXPENSE_ACCOUNT_CODE_MAP.get(db_expense.functional_category, "6601")
        credit_code = "2241" if db_expense.payment_method == "private_advance" else "2211" if db_expense.category == "工资" else "2202"
        post_journal(db, account_id, "expense", {
            "amount": db_expense.amount_l1,
            "date": db_expense.expense_date_l1.strftime("%Y-%m-%d") if db_expense.expense_date_l1 else "",
            "expense_account_code": expense_code,
            "credit_account_code": credit_code,
            "bank_account_id": None,
            "partner_id": None,
            "partner_type": None,
            "source_model": "expense",
            "source_id": db_expense.id,
        })

        log_op(db, account_id, "create", "expense", db_expense.id,
             f"创建费用:{db_expense.category} {db_expense.amount_l1}", operator=cmd.operator)

        db.refresh(db_expense)
        return OperationResult(
            operation=OperationType.CREATE,
            entity_type=EntityType.EXPENSE,
            entity_id=db_expense.id,
            summary=f"费用创建成功，类别：{db_expense.category}，金额 {db_expense.amount_l1}",
            ai_hint="费用已创建，状态为未付款。如需付款，请调用 POST /api/payments。",
            data={
                "id": db_expense.id,
                "account_id": db_expense.account_id,
                "category": db_expense.category,
                "functional_category": db_expense.functional_category,
                "amount": float(db_expense.amount_l1),
                "expense_date": db_expense.expense_date_l1.isoformat() if db_expense.expense_date_l1 else None,
                "has_invoice": linkage_has_invoice(db, account_id, "expense", db_expense.id),
                "payment_method": db_expense.payment_method,
                "payment_status": db_expense.payment_status,
                "description": db_expense.description,
                "image_url": db_expense.image_url or "",
                "created_at": db_expense.created_at.isoformat() if db_expense.created_at else None,
            },
            changes={"payable": {"amount": f"+{db_expense.amount_l1}"}},
        ).to_dict()


@dataclass
class UpdateExpense(Command):
    expense_id: Optional[int] = None
    expense_update: Optional[ExpenseUpdate] = None


@register(UpdateExpense)
class UpdateExpenseHandler(CommandHandler):
    def handle(self, cmd: UpdateExpense, db: Any) -> Any:
        account_id = cmd.account_id
        expense_id = cmd.expense_id
        expense_update = cmd.expense_update

        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.account_id == account_id,
        ).first()
        if not expense:
            raise BusinessError(code=ErrorCode.EXPENSE_NOT_FOUND, data={"expense_id": expense_id})

        if expense.payment_status == "paid":
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="已付款费用禁止修改",
                ai_instruction="STOP_RETRYING. 该费用已付款，禁止修改。如需调整，请创建新的费用记录。",
            )

        update_data = expense_update.model_dump(exclude_unset=True)
        if expense_update.category is not None and expense_update.category not in EXPENSE_CATEGORIES:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                data={"details": f"费用类别 '{expense_update.category}' 不合法，合法值: {EXPENSE_CATEGORIES}"},
            )

        for field_name, value in update_data.items():
            setattr(expense, field_name, value)

        log_op(db, account_id, "update", "expense", expense.id,
             f"更新费用:{expense.category} {expense.amount_l1}", operator=cmd.operator)
        db.refresh(expense)

        return OperationResult(
            operation=OperationType.UPDATE,
            entity_type=EntityType.EXPENSE,
            entity_id=expense.id,
            summary=f"费用更新成功，类别：{expense.category}，金额 {expense.amount_l1}",
            ai_hint="费用已更新。",
            data={"id": expense.id, "category": expense.category, "amount": float(expense.amount_l1)},
        ).to_dict()


@dataclass
class ReverseExpense(Command):
    expense_id: Optional[int] = None


@register(ReverseExpense)
class ReverseExpenseHandler(CommandHandler):
    def handle(self, cmd: ReverseExpense, db: Any) -> Any:
        account_id = cmd.account_id
        expense_id = cmd.expense_id

        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.account_id == account_id,
        ).first()
        if not expense:
            raise BusinessError(code=ErrorCode.EXPENSE_NOT_FOUND, data={"expense_id": expense_id})

        if getattr(expense, "is_reversed", False):
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"费用 #{expense_id} 已被冲红，不可重复操作",
                ai_instruction="STOP_RETRYING. 该费用已冲红。",
            )

        reverse_journal(db, account_id, "expense", expense_id)
        expense.is_reversed = True
        expense.reversed_at = datetime.now()

        log_op(db, account_id, "reverse", "expense", expense_id,
             f"红冲费用: {expense.category} {expense.amount_l1}", operator=cmd.operator)

        return OperationResult(
            operation=OperationType.UPDATE,
            entity_type=EntityType.EXPENSE,
            entity_id=expense_id,
            summary=f"费用 #{expense_id} 已红冲",
            ai_hint="费用凭证已冲红，原费用记录保留（审计可追溯）。",
            data={"expense_id": expense_id, "is_reversed": True},
        ).to_dict()


@dataclass
class DeleteExpense(Command):
    expense_id: Optional[int] = None


@register(DeleteExpense)
class DeleteExpenseHandler(CommandHandler):
    def handle(self, cmd: DeleteExpense, db: Any) -> Any:
        account_id = cmd.account_id
        expense_id = cmd.expense_id

        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.account_id == account_id,
        ).first()
        if not expense:
            raise BusinessError(code=ErrorCode.EXPENSE_NOT_FOUND, data={"expense_id": expense_id})

        if expense.image_url:
            delete_old_image(expense.image_url)

        db.delete(expense)
        log_op(db, account_id, "delete", "expense", expense.id,
             f"删除费用:{expense.category} {expense.amount_l1}", operator=cmd.operator)

        return OperationResult(
            operation=OperationType.DELETE,
            entity_type=EntityType.EXPENSE,
            entity_id=expense_id,
            summary=f"费用删除成功，类别：{expense.category}，金额 {expense.amount_l1}",
            ai_hint="费用已删除。",
            data={"expense_id": expense_id, "category": expense.category},
        ).to_dict()


# ═══════════════════════════════════════════════════════════
# Payment Commands
# ═══════════════════════════════════════════════════════════

@dataclass
class CreatePayment(Command):
    data: Optional[PaymentCreate] = None


@register(CreatePayment)
class CreatePaymentHandler(CommandHandler):
    @writes("Payment.amount_l1", tier=TIER_L1, source="external")
    @writes("Payment.withholding_tax_amount_l1", tier=TIER_L1, source="external")
    @writes("Payment.payment_date_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: CreatePayment, db: Any) -> Any:
        account_id = cmd.account_id
        data = cmd.data

        if data.withholding_tax_amount > 0 and data.payment_type != "salary":
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"withholding_tax_amount 仅 payment_type=salary 可用,当前 payment_type={data.payment_type}",
                ai_instruction="STOP_RETRYING. 代扣个税只在发工资时使用,其他付款类型不应传 withholding_tax_amount。",
            )

        payment = Payment(
            account_id=account_id,
            payment_type=data.payment_type,
            related_entity_type=data.related_entity_type,
            related_entity_id=data.related_entity_id,
            amount_l1=to_decimal(data.amount),
            withholding_tax_amount_l1=to_decimal(data.withholding_tax_amount),
            payment_method=data.payment_method,
            payment_date_l1=data.payment_date,
            bank_account_id=data.bank_account_id,
            description=data.description,
        )
        db.add(payment)
        db.flush()

        if not data.bank_account_id:
            default_bank = db.query(BankAccount).filter(
                BankAccount.account_id == account_id,
            ).first()
            if default_bank:
                data.bank_account_id = default_bank.id

        if data.bank_account_id:
            # 经 BankEngine.record_transaction 统一入口写入（含行锁、透支校验、余额同步）
            bank_transaction = BankEngine(db, account_id).record_transaction(
                bank_account_id=data.bank_account_id,
                transaction_type="outflow",
                amount=data.amount,
                transaction_date=data.payment_date,
                description=f"付款: {data.description}",
                flow_category="operating",
                related_entity_type="payment",
                related_entity_id=payment.id,
            )
            payment.bank_transaction_id = bank_transaction.id

        if data.related_entity_type == "expense":
            expense = db.query(Expense).filter(
                Expense.id == data.related_entity_id,
                Expense.account_id == account_id,
            ).first()
            if expense:
                expense.payment_status = "paid"
                expense.payment_id = payment.id

        if data.related_entity_type == "purchase_order":
            purchase_order = db.query(PurchaseOrder).filter(
                PurchaseOrder.id == data.related_entity_id,
                PurchaseOrder.account_id == account_id,
            ).first()
            if purchase_order:
                purchase_order.payment_status = "paid"

        if data.payment_type == "salary":
            debit_code = "2211"
        elif data.payment_type == "tax":
            debit_code = "2221"
        elif data.payment_type == "expense" and data.related_entity_type == "expense":
            adv = db.query(Expense).filter(Expense.id == data.related_entity_id).first()
            debit_code = "2241" if adv and adv.payment_method == "private_advance" else "2202"
        else:
            debit_code = "2202"

        post_journal(db, account_id, "payment", {
            "amount": to_decimal(data.amount),
            "withholding_tax_amount": to_decimal(data.withholding_tax_amount),
            "date": data.payment_date.strftime("%Y-%m-%d"),
            "debit_account_code": debit_code,
            "partner_id": data.related_entity_id,
            "partner_type": "supplier",
            "bank_account_id": data.bank_account_id,
        })

        db.flush()
        log_op(db, account_id, "create", "payment", payment.id,
             f"创建付款: {data.payment_type} {data.amount}", operator=cmd.operator)
        db.refresh(payment)

        changes = {"cash": {"amount": f"-{data.amount}"}}
        if data.related_entity_type == "expense":
            changes["payable"] = {"amount": f"-{data.amount}"}
        elif data.related_entity_type == "purchase_order":
            changes["payable"] = {"amount": f"-{data.amount}"}
        elif data.related_entity_type == "tax_payable":
            changes["tax_payable"] = {"amount": f"-{data.amount}"}
            changes["note"] = "缴税:借应交税费,贷银行存款,清负债不碰利润表"

        return OperationResult(
            operation=OperationType.CREATE,
            entity_type=EntityType.PAYMENT,
            entity_id=payment.id,
            summary=f"付款成功，金额 {data.amount}，类型 {data.payment_type}",
            ai_hint="付款已完成，银行余额已减少。",
            data=PaymentOut.model_validate(payment).model_dump(),
            changes=changes,
        ).to_dict()


@dataclass
class ReversePayment(Command):
    payment_id: Optional[int] = None


@register(ReversePayment)
class ReversePaymentHandler(CommandHandler):
    def handle(self, cmd: ReversePayment, db: Any) -> Any:
        account_id = cmd.account_id
        payment_id = cmd.payment_id

        reversal = reverse_single_payment(db, account_id, payment_id)
        if not reversal:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"payment_id": payment_id})
        log_op(db, account_id, "reverse", "payment", payment_id,
             f"红冲付款: {reversal.amount_l1}", operator=cmd.operator)
        return {"status": "reversed", "reversal_id": reversal.id}


# ═══════════════════════════════════════════════════════════
# Receipt Commands
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateReceipt(Command):
    data: Optional[ReceiptCreate] = None


@register(CreateReceipt)
class CreateReceiptHandler(CommandHandler):
    @writes("Receipt.amount_l1", tier=TIER_L1, source="external")
    @writes("Receipt.receipt_date_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: CreateReceipt, db: Any) -> Any:
        account_id = cmd.account_id
        data = cmd.data

        receipt = Receipt(
            account_id=account_id,
            receipt_type=data.receipt_type,
            related_entity_type=data.related_entity_type,
            related_entity_id=data.related_entity_id,
            amount_l1=to_decimal(data.amount),
            receipt_method=data.receipt_method,
            receipt_date_l1=data.receipt_date,
            bank_account_id=data.bank_account_id,
            description=data.description,
        )
        db.add(receipt)
        db.flush()

        if not data.bank_account_id:
            default_bank = db.query(BankAccount).filter(
                BankAccount.account_id == account_id,
            ).first()
            if default_bank:
                data.bank_account_id = default_bank.id

        if data.bank_account_id:
            # 经 BankEngine.record_transaction 统一入口写入（含行锁、余额同步）
            bank_transaction = BankEngine(db, account_id).record_transaction(
                bank_account_id=data.bank_account_id,
                transaction_type="inflow",
                amount=data.amount,
                transaction_date=data.receipt_date,
                description=f"收款: {data.description}",
                flow_category="operating",
                related_entity_type="receipt",
                related_entity_id=receipt.id,
            )
            receipt.bank_transaction_id = bank_transaction.id

        if data.related_entity_type == "sale_order":
            sale_order = db.query(SaleOrder).filter(
                SaleOrder.id == data.related_entity_id,
                SaleOrder.account_id == account_id,
            ).first()
            if sale_order:
                sale_order.payment_status = "paid"

        post_journal(db, account_id, "receipt", {
            "amount": to_decimal(data.amount),
            "date": data.receipt_date.strftime("%Y-%m-%d"),
            "partner_id": data.related_entity_id,
            "bank_account_id": data.bank_account_id,
        })

        db.flush()
        log_op(db, account_id, "create", "receipt", receipt.id,
             f"创建收款: {data.receipt_type} {data.amount}", operator=cmd.operator)
        db.refresh(receipt)

        return OperationResult(
            operation=OperationType.CREATE,
            entity_type=EntityType.RECEIPT,
            entity_id=receipt.id,
            summary=f"收款成功，金额 {data.amount}，类型 {data.receipt_type}",
            ai_hint="收款已完成，银行余额已增加。",
            data=ReceiptOut.model_validate(receipt).model_dump(),
            changes={"cash": {"amount": f"+{data.amount}"}},
        ).to_dict()


@dataclass
class ReverseReceipt(Command):
    receipt_id: Optional[int] = None


@register(ReverseReceipt)
class ReverseReceiptHandler(CommandHandler):
    def handle(self, cmd: ReverseReceipt, db: Any) -> Any:
        account_id = cmd.account_id
        receipt_id = cmd.receipt_id

        reversal = reverse_single_receipt(db, account_id, receipt_id)
        if not reversal:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"receipt_id": receipt_id})
        log_op(db, account_id, "reverse", "receipt", receipt_id,
             f"红冲收款: {reversal.amount_l1}", operator=cmd.operator)
        return {"status": "reversed", "reversal_id": reversal.id}
