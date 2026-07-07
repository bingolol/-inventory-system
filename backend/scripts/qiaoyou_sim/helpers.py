"""巧游电子科技业务模拟 — 共用工具与基础数据

设计原则：
- 直接通过 ORM + dispatch(command) 创建业务对象，与 routers 调用同一入口
- 商品/客户/供应商/银行账户在阶段1一次性建立，后续阶段按 id 引用
- 业务日期显式传入，禁止用 datetime.now() 默认值
"""
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
import uuid

import models
from commands.base import dispatch
from commands.orders import CreateOrder, CreateInvoice
from commands.cash_commands import CreateExpense, CreateReceipt
from commands.bank_commands import CreateBankEntry
from schemas.order import SaleOrderCreate, SaleItemCreate, PurchaseOrderCreate, PurchaseItemCreate
from schemas.expense import ExpenseCreate
from schemas.receipt import ReceiptCreate
from schemas.finance import FixedAssetCreate
from crud.finance.fixed_assets import create_fixed_asset
from uow import unit_of_work

Q2 = Decimal("0.01")


# ── 基础数据 ──

PRODUCTS = {
    "信息系统服务": None,    # 服务类，track_inventory=False
    "修理修配劳务": None,    # 服务类
    "微电子组件": None,      # 实物商品
    "其他加工劳务": None,    # 服务类
    "维修备件": None,        # 实物商品
}

CUSTOMERS = {
    "中国联通宜宾分公司": None,
    "四川南山射钉紧固器材有限公司": None,
}

SUPPLIERS = {
    "吴江恒净净化设备经营部": None,
    "临泉县嘉涵商贸有限公司": None,
    "乐清市申港电气厂": None,
    "博控科技（淮安）有限公司": None,
}

# 银行账户 ID（阶段1建立后填充）
BANK_ACCOUNT_ID: Optional[int] = None


def setup_basic_data(db, account_id: int) -> None:
    """阶段1：建立商品/客户/供应商/银行账户基础数据"""
    global PRODUCTS, CUSTOMERS, SUPPLIERS, BANK_ACCOUNT_ID

    # 商品（track_inventory 决定会计科目：True→1405 库存，False→6601 费用）
    product_defs = [
        ("信息系统服务", "服务", False),
        ("修理修配劳务", "服务", False),
        ("微电子组件", "商品", True),
        ("其他加工劳务", "服务", False),
        ("维修备件", "商品", True),
    ]
    for name, category, track_inv in product_defs:
        p = models.Product(
            account_id=account_id,
            name=name,
            sku=f"SKU-{name[:4]}",
            category=category,
            unit="个",
            track_inventory_l3=track_inv,
        )
        db.add(p)
        db.flush()
        PRODUCTS[name] = p.id

    # 客户
    for name in CUSTOMERS:
        c = models.Customer(account_id=account_id, name=name)
        db.add(c)
        db.flush()
        CUSTOMERS[name] = c.id

    # 供应商
    for name in SUPPLIERS:
        s = models.Supplier(account_id=account_id, name=name)
        db.add(s)
        db.flush()
        SUPPLIERS[name] = s.id

    # 银行账户
    ba = models.BankAccount(
        account_id=account_id,
        bank_name="中国银行宜宾分行",
        account_number="6217 0000 0000 0000",
    )
    db.add(ba)
    db.flush()
    BANK_ACCOUNT_ID = ba.id

    db.flush()


# ── 业务创建工具 ──

def _split_amounts(amount_with_tax: Decimal, tax_rate: Decimal):
    """价税分离：含税金额 → (不含税金额, 税额)"""
    amount_without_tax = (amount_with_tax / (Decimal("1") + tax_rate)).quantize(Q2, rounding=ROUND_HALF_UP)
    tax_amount = (amount_with_tax - amount_without_tax).quantize(Q2, rounding=ROUND_HALF_UP)
    return amount_without_tax, tax_amount


def create_sale_order(db, account_id: int, customer_name: str, sale_date: datetime,
                      items: list, has_invoice: bool = True,
                      notes: str = "") -> models.SaleOrder:
    """创建销售单（发票驱动：先创建发票，自动生成销售单）

    items: [(product_name, quantity, unit_price, tax_rate, item_notes), ...]
    unit_price 为含税单价
    发票是销项税的真相源（BR-1, BR-27）
    """
    invoice_items = [
        {
            "product_id": PRODUCTS[pn],
            "quantity": qty,
            "unit_price": str(price),
            "tax_rate": str(rate),
        }
        for pn, qty, price, rate, _ in items
    ]

    if has_invoice:
        # 价税分离
        amount_with_tax = sum(
            Decimal(str(qty)) * Decimal(str(price))
            for _, qty, price, _, _ in items
        ).quantize(Q2, rounding=ROUND_HALF_UP)
        tax_rate = Decimal(str(items[0][3]))
        amount_without_tax, tax_amount = _split_amounts(amount_with_tax, tax_rate)

        # 发票号唯一（uuid 防止同日多笔冲突）
        invoice_no = f"INV-OUT-{sale_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

        with unit_of_work(db):
            invoice = dispatch(CreateInvoice(
                account_id=account_id,
                operator="sim",
                invoice_no=invoice_no,
                direction="out",
                invoice_type="ordinary",
                tax_rate=tax_rate,
                amount_without_tax=amount_without_tax,
                tax_amount=tax_amount,
                amount_with_tax=amount_with_tax,
                counterparty_name=customer_name,
                issue_date=sale_date.date() if isinstance(sale_date, datetime) else sale_date,
                sale_order_action="auto_create",
                items=invoice_items,
            ), db)
        db.flush()
        # 返回关联的销售单
        order = db.query(models.SaleOrder).filter(
            models.SaleOrder.id == invoice.related_order_id
        ).first()
        return order

    # 无发票模式：直接创建订单
    with unit_of_work(db):
        order = dispatch(CreateOrder(
            order_type="sale",
            account_id=account_id,
            operator="sim",
            customer_id=CUSTOMERS[customer_name],
            sale_date=sale_date,
            has_invoice=False,
            notes=notes,
            payment_status="unpaid",
            items=invoice_items,
        ), db)
    db.flush()
    return order


def create_purchase_order(db, account_id: int, supplier_name: str,
                          purchase_date: datetime, items: list,
                          has_invoice: bool = True,
                          notes: str = "") -> models.PurchaseOrder:
    """创建采购单（发票驱动：先创建发票，自动生成采购单）

    items: [(product_name, quantity, unit_price, tax_rate, item_notes), ...]
    小规模纳税人：unit_price 含税，tax_rate=0.01（减按1%）
    发票是进项税的真相源（BR-1, BR-27）
    """
    invoice_items = [
        {
            "product_id": PRODUCTS[pn],
            "quantity": qty,
            "unit_price": str(price),
            "tax_rate": str(rate),
        }
        for pn, qty, price, rate, _ in items
    ]

    if has_invoice:
        # 价税分离
        amount_with_tax = sum(
            Decimal(str(qty)) * Decimal(str(price))
            for _, qty, price, _, _ in items
        ).quantize(Q2, rounding=ROUND_HALF_UP)
        tax_rate = Decimal(str(items[0][3]))
        amount_without_tax, tax_amount = _split_amounts(amount_with_tax, tax_rate)

        invoice_no = f"INV-IN-{purchase_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

        with unit_of_work(db):
            invoice = dispatch(CreateInvoice(
                account_id=account_id,
                operator="sim",
                invoice_no=invoice_no,
                direction="in",
                invoice_type="ordinary",
                tax_rate=tax_rate,
                amount_without_tax=amount_without_tax,
                tax_amount=tax_amount,
                amount_with_tax=amount_with_tax,
                counterparty_name=supplier_name,
                issue_date=purchase_date.date() if isinstance(purchase_date, datetime) else purchase_date,
                purchase_order_action="auto_create",
                items=invoice_items,
            ), db)
        db.flush()
        order = db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.id == invoice.related_order_id
        ).first()
        return order

    # 无发票模式
    with unit_of_work(db):
        order = dispatch(CreateOrder(
            order_type="purchase",
            account_id=account_id,
            operator="sim",
            supplier_id=SUPPLIERS[supplier_name],
            purchase_date=purchase_date,
            notes=notes,
            items=invoice_items,
        ), db)
    db.flush()
    return order


def create_fixed_asset_purchase(db, account_id: int, name: str, cost: Decimal,
                                purchase_date: date, notes: str,
                                useful_life: int = 60,
                                salvage_rate: Decimal = Decimal("0.05")) -> models.FixedAsset:
    """创建固定资产（个人垫付时 payment_method=private_advance）

    会计分录：Dr 1601 固定资产 / Cr 2202 应付账款（公司采购）或 2241 其他应付款（个人垫付）
    """
    asset_code = f"FA-{purchase_date.strftime('%Y%m%d')}-{name[:6]}"
    data = FixedAssetCreate(
        asset_code=asset_code,
        name=name,
        category="电子设备",
        original_value=cost,
        salvage_rate=salvage_rate,
        useful_life=useful_life,
        depreciation_method="年限平均法",
        start_date=purchase_date.strftime("%Y-%m-%d"),
        status="在用",
    )
    with unit_of_work(db):
        asset = create_fixed_asset(db, account_id, data, operator="sim")
    db.flush()
    return asset


def create_expense(db, account_id: int, category: str, amount: float,
                   expense_date: date, description: str,
                   functional_category: str = "管理费用",
                   payment_method: str = "company") -> models.Expense:
    """创建费用（房租/水电等）"""
    with unit_of_work(db):
        result = dispatch(CreateExpense(
            account_id=account_id,
            operator="sim",
            expense=ExpenseCreate(
                category=category,
                functional_category=functional_category,
                amount=Decimal(str(amount)),
                expense_date=datetime.combine(expense_date, datetime.min.time()),
                payment_method=payment_method,
                description=description,
            ),
        ), db)
    db.flush()
    return result


def create_customer_payment(db, account_id: int, customer_name: str,
                            sale_order_id: int, amount: float,
                            payment_date: date) -> models.Receipt:
    """客户收款（银行流入）"""
    with unit_of_work(db):
        result = dispatch(CreateReceipt(
            account_id=account_id,
            operator="sim",
            data=ReceiptCreate(
                receipt_type="sale",
                related_entity_type="sale_order",
                related_entity_id=sale_order_id,
                amount=Decimal(str(amount)),
                receipt_method="company",
                receipt_date=datetime.combine(payment_date, datetime.min.time()),
                bank_account_id=BANK_ACCOUNT_ID,
                description=f"{customer_name} 收款",
            ),
        ), db)
    db.flush()
    return result


def create_bank_fee(db, account_id: int, amount: float, fee_date: date,
                    description: str) -> models.BankTransaction:
    """银行扣款（开户费/年费等）

    通过 CreateBankEntry 过账到总账 6603 财务费用（借方）/ 1002 银行存款（贷方），
    确保 GL 与银行流水同步。
    """
    with unit_of_work(db):
        result = dispatch(CreateBankEntry(
            account_id=account_id,
            operator="sim",
            entry_type="bank_fee",
            amount=amount,
            transaction_date=fee_date.strftime("%Y-%m-%d"),
            description=description,
        ), db)
    tx = db.get(models.BankTransaction, result["entity_id"])
    db.flush()
    return tx


def create_bank_interest(db, account_id: int, amount: float,
                         interest_date: date) -> models.BankTransaction:
    """银行利息收入

    通过 CreateBankEntry 过账到总账 1002 银行存款（借方）/ 6603 财务费用（贷方），
    冲减财务费用。会计准则要求利息收入贷记 6603，不进 6301 营业外收入。
    """
    with unit_of_work(db):
        result = dispatch(CreateBankEntry(
            account_id=account_id,
            operator="sim",
            entry_type="interest_income",
            amount=amount,
            transaction_date=interest_date.strftime("%Y-%m-%d"),
            description="银行利息收入",
        ), db)
    tx = db.get(models.BankTransaction, result["entity_id"])
    db.flush()
    return tx
