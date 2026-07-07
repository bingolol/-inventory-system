"""MCP tools — 严格对齐 qiaoyou_sim/helpers.py 的调用路径

设计铁律:
- 每个 tool 对应 sim 里的一个 helper 函数, 调用路径完全一致
- 发票驱动: create_sale_order_with_invoice / create_purchase_order_with_invoice 都走
  CreateInvoice(direction='out'/'in', sale_order_action='auto_create') 路径
- 价税分离: tool 内置 _split_amounts, agent 只需传含税金额 + 税率
- 会计分录预告: 每个写 tool 返回 accounting_hint, 说明借贷科目
- operator='ai': 所有写操作走审计路径

18 个 tool:
  上下文 (1):  set_current_account
  基础数据 (5): setup_basic_data, list_products, list_customers, list_suppliers, list_bank_accounts
  销售 (2):    create_sale_order_with_invoice, create_receipt
  采购 (1):    create_purchase_order_with_invoice
  费用 (1):    create_expense
  银行 (1):    create_bank_entry
  固定资产 (2): create_fixed_asset, batch_depreciate
  税务申报 (2): declare_vat, declare_surcharge
  月结 (1):    month_end_close
  报表 (2):    get_balance_sheet, get_income_statement
"""
import logging
import uuid
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from errors import BusinessError

from . import tool_dispatcher
from . import account_context

logger = logging.getLogger("mcp_server.tools")

Q2 = Decimal("0.01")


# ──────────────────────────────────────────────────────────────
# 辅助: 价税分离 (与 sim helpers._split_amounts 完全一致)
# ──────────────────────────────────────────────────────────────
def _split_amounts(amount_with_tax: Decimal, tax_rate: Decimal):
    """价税分离: 含税金额 → (不含税金额, 税额)

    与 qiaoyou_sim/helpers.py:_split_amounts 完全一致。
    """
    amount_without_tax = (amount_with_tax / (Decimal("1") + tax_rate)).quantize(Q2, rounding=ROUND_HALF_UP)
    tax_amount = (amount_with_tax - amount_without_tax).quantize(Q2, rounding=ROUND_HALF_UP)
    return amount_without_tax, tax_amount


def _parse_date(d):
    """日期参数转 date 对象 (兼容 str / date / datetime)。"""
    if d is None:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d").date()
    raise BusinessError(code=None, message=f"无法解析日期: {d}")


def _to_datetime(d, end_of_day=False):
    """日期参数转 datetime (用于需要 datetime 的字段)。"""
    d_obj = _parse_date(d)
    if d_obj is None:
        return None
    if end_of_day:
        return datetime.combine(d_obj, datetime.max.time())
    return datetime.combine(d_obj, datetime.min.time())


# ──────────────────────────────────────────────────────────────
# 辅助: 安全序列化
# ──────────────────────────────────────────────────────────────
def _safe_serialize(obj: Any, _depth: int = 0) -> Any:
    """递归序列化, 处理 Decimal/datetime/ORM 模型。"""
    if _depth > 10:
        return "<truncated>"
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [_safe_serialize(x, _depth + 1) for x in obj]
    if isinstance(obj, dict):
        return {k: _safe_serialize(v, _depth + 1) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return {k: _safe_serialize(v, _depth + 1) for k, v in d.items()}
    return str(obj)


# ══════════════════════════════════════════════════════════════
# 1. 上下文: set_current_account
# ══════════════════════════════════════════════════════════════
def set_current_account(arguments: dict) -> dict:
    """设置当前账本上下文。"""
    account_id = arguments.get("account_id")
    if not account_id or not isinstance(account_id, int):
        raise BusinessError(code=None, message="参数 account_id 必填且为整数")

    def _verify(db, _aid):
        accounts = account_context.list_all_accounts(db)
        if not any(a["id"] == account_id for a in accounts):
            raise BusinessError(
                code=None,
                message=f"账本 ID={account_id} 不存在",
                data={"available_accounts": accounts},
            )
        return accounts

    accounts = tool_dispatcher.run_readonly(_verify)
    account_context.set_current_account_id(account_id)
    target = next((a for a in accounts if a["id"] == account_id), None)
    return {"ok": True, "current_account_id": account_id, "current_account": target}


# ══════════════════════════════════════════════════════════════
# 2-6. 基础数据: setup_basic_data / list_*
# ══════════════════════════════════════════════════════════════
def setup_basic_data(arguments: dict) -> dict:
    """建立基础数据 (商品/客户/供应商/银行账户)。

    对应 sim helpers.setup_basic_data。
    与 sim 一致: 商品通过 ORM 创建, track_inventory_l3 决定会计科目。
    """
    account_id = account_context.require_account_id()

    products = arguments.get("products", [])
    customers = arguments.get("customers", [])
    suppliers = arguments.get("suppliers", [])
    bank_account = arguments.get("bank_account", {})

    if not products and not customers and not suppliers and not bank_account:
        raise BusinessError(code=None, message="至少需要提供一项基础数据 (products/customers/suppliers/bank_account)")

    def _create(db, _aid):
        import models
        result = {"products": [], "customers": [], "suppliers": [], "bank_account": None}
        # 商品 (与 sim 一致: track_inventory_l3 决定 1405 库存 / 6601 费用)
        for p in products:
            obj = models.Product(
                account_id=account_id,
                name=p["name"],
                sku=p.get("sku", f"SKU-{p['name'][:4]}"),
                category=p.get("category", "商品"),
                unit=p.get("unit", "个"),
                track_inventory_l3=p.get("track_inventory", True),
            )
            db.add(obj)
            db.flush()
            result["products"].append({"id": obj.id, "name": obj.name, "track_inventory": obj.track_inventory_l3})
        # 客户
        for name in customers:
            c = models.Customer(account_id=account_id, name=name)
            db.add(c)
            db.flush()
            result["customers"].append({"id": c.id, "name": c.name})
        # 供应商
        for name in suppliers:
            s = models.Supplier(account_id=account_id, name=name)
            db.add(s)
            db.flush()
            result["suppliers"].append({"id": s.id, "name": s.name})
        # 银行账户
        if bank_account:
            ba = models.BankAccount(
                account_id=account_id,
                bank_name=bank_account.get("bank_name", ""),
                account_number=bank_account.get("account_number", ""),
            )
            db.add(ba)
            db.flush()
            result["bank_account"] = {"id": ba.id, "bank_name": ba.bank_name, "account_number": ba.account_number}
        return result

    # setup_basic_data 是写操作, 但走 ORM 不是 Command, 需要直接开 Session + 写权限
    from database import SessionLocal, _request_write_perm
    db = SessionLocal()
    token = _request_write_perm.set(True)
    try:
        result = _create(db, account_id)
        db.commit()
        return {
            "ok": True,
            "operation": "setup_basic_data",
            "result": result,
            "accounting_hint": "基础数据创建不生成会计凭证, 仅建立主数据。",
        }
    except Exception:
        db.rollback()
        raise
    finally:
        _request_write_perm.reset(token)
        db.close()


def list_products(arguments: dict) -> dict:
    """列出当前账本所有商品。"""
    def _query(db, aid):
        import models
        items = db.query(models.Product).filter(
            models.Product.account_id == aid
        ).order_by(models.Product.id.asc()).all()
        return [{
            "id": p.id, "name": p.name, "sku": p.sku,
            "category": p.category, "unit": p.unit,
            "track_inventory": p.track_inventory_l3,
            "purchase_price": float(p.purchase_price_l3) if p.purchase_price_l3 else 0,
        } for p in items]
    return {"ok": True, "products": tool_dispatcher.run_readonly(_query)}


def list_customers(arguments: dict) -> dict:
    """列出当前账本所有客户。"""
    def _query(db, aid):
        import models
        items = db.query(models.Customer).filter(
            models.Customer.account_id == aid
        ).order_by(models.Customer.id.asc()).all()
        return [{"id": c.id, "name": c.name} for c in items]
    return {"ok": True, "customers": tool_dispatcher.run_readonly(_query)}


def list_suppliers(arguments: dict) -> dict:
    """列出当前账本所有供应商。"""
    def _query(db, aid):
        import models
        items = db.query(models.Supplier).filter(
            models.Supplier.account_id == aid
        ).order_by(models.Supplier.id.asc()).all()
        return [{"id": s.id, "name": s.name} for s in items]
    return {"ok": True, "suppliers": tool_dispatcher.run_readonly(_query)}


def list_bank_accounts(arguments: dict) -> dict:
    """列出当前账本所有银行账户。"""
    def _query(db, aid):
        import models
        items = db.query(models.BankAccount).filter(
            models.BankAccount.account_id == aid
        ).order_by(models.BankAccount.id.asc()).all()
        return [{"id": b.id, "bank_name": b.bank_name, "account_number": b.account_number} for b in items]
    return {"ok": True, "bank_accounts": tool_dispatcher.run_readonly(_query)}


# ══════════════════════════════════════════════════════════════
# 7. 销售: create_sale_order_with_invoice (发票驱动)
# ══════════════════════════════════════════════════════════════
def create_sale_order_with_invoice(arguments: dict) -> dict:
    """创建销售单 (发票驱动: 先创建发票, 自动生成销售单)。

    对应 sim helpers.create_sale_order(has_invoice=True)。
    调用路径: dispatch(CreateInvoice(direction='out', sale_order_action='auto_create'))
    发票是销项税真相源 (BR-1, BR-27)。

    参数:
        customer_name: str  客户名称
        sale_date: str  销售日期 (YYYY-MM-DD)
        items: list  商品明细 [{product_id, quantity, unit_price, tax_rate, notes?}]
                     unit_price 为含税单价
        invoice_type: str  发票类型 (ordinary/special, 默认 ordinary)
        notes: str  备注
    """
    from commands.orders import CreateInvoice

    customer_name = arguments.get("customer_name")
    sale_date_str = arguments.get("sale_date")
    items = arguments.get("items", [])

    if not customer_name:
        raise BusinessError(code=None, message="customer_name 必填")
    if not sale_date_str:
        raise BusinessError(code=None, message="sale_date 必填 (YYYY-MM-DD)")
    if not items:
        raise BusinessError(code=None, message="items 不能为空")

    sale_date = _parse_date(sale_date_str)

    # 价税分离 (与 sim 一致)
    amount_with_tax = sum(
        Decimal(str(it["quantity"])) * Decimal(str(it["unit_price"]))
        for it in items
    ).quantize(Q2, rounding=ROUND_HALF_UP)
    tax_rate = Decimal(str(items[0]["tax_rate"]))
    amount_without_tax, tax_amount = _split_amounts(amount_with_tax, tax_rate)

    # 发票号唯一 (与 sim 一致)
    invoice_no = f"INV-OUT-{sale_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    invoice_items = [
        {
            "product_id": it["product_id"],
            "quantity": it["quantity"],
            "unit_price": str(it["unit_price"]),
            "tax_rate": str(it.get("tax_rate", items[0]["tax_rate"])),
        }
        for it in items
    ]

    result = tool_dispatcher.execute_command(
        CreateInvoice,
        invoice_no=invoice_no,
        direction="out",
        invoice_type=arguments.get("invoice_type", "ordinary"),
        tax_rate=tax_rate,
        amount_without_tax=amount_without_tax,
        tax_amount=tax_amount,
        amount_with_tax=amount_with_tax,
        counterparty_name=customer_name,
        issue_date=sale_date,
        sale_order_action="auto_create",
        items=invoice_items,
        notes=arguments.get("notes", ""),
    )
    return {
        "ok": True,
        "operation": "create_sale_order_with_invoice",
        "result": _safe_serialize(result),
        "amount_with_tax": float(amount_with_tax),
        "tax_amount": float(tax_amount),
        "accounting_hint": (
            "发票驱动: 先开发票自动生成销售单。"
            "会计影响: 借:应收账款 贷:主营业务收入+应交税费-销项税额; "
            "同时借:主营业务成本 贷:库存商品 (实物商品, 按 unit_cost 加权平均)。"
            "铁律: COGS 必须用 SaleItem.unit_cost (锁定成本), 禁止用 Product.purchase_price。"
        ),
    }


# ══════════════════════════════════════════════════════════════
# 8. 采购: create_purchase_order_with_invoice (发票驱动)
# ══════════════════════════════════════════════════════════════
def create_purchase_order_with_invoice(arguments: dict) -> dict:
    """创建采购单 (发票驱动: 先创建发票, 自动生成采购单)。

    对应 sim helpers.create_purchase_order(has_invoice=True)。
    调用路径: dispatch(CreateInvoice(direction='in', purchase_order_action='auto_create'))
    发票是进项税真相源 (BR-1, BR-27)。

    参数:
        supplier_name: str  供应商名称
        purchase_date: str  采购日期 (YYYY-MM-DD)
        items: list  商品明细 [{product_id, quantity, unit_price, tax_rate, notes?}]
        invoice_type: str  发票类型 (默认 ordinary)
        notes: str  备注
    """
    from commands.orders import CreateInvoice

    supplier_name = arguments.get("supplier_name")
    purchase_date_str = arguments.get("purchase_date")
    items = arguments.get("items", [])

    if not supplier_name:
        raise BusinessError(code=None, message="supplier_name 必填")
    if not purchase_date_str:
        raise BusinessError(code=None, message="purchase_date 必填 (YYYY-MM-DD)")
    if not items:
        raise BusinessError(code=None, message="items 不能为空")

    purchase_date = _parse_date(purchase_date_str)

    amount_with_tax = sum(
        Decimal(str(it["quantity"])) * Decimal(str(it["unit_price"]))
        for it in items
    ).quantize(Q2, rounding=ROUND_HALF_UP)
    tax_rate = Decimal(str(items[0]["tax_rate"]))
    amount_without_tax, tax_amount = _split_amounts(amount_with_tax, tax_rate)

    invoice_no = f"INV-IN-{purchase_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    invoice_items = [
        {
            "product_id": it["product_id"],
            "quantity": it["quantity"],
            "unit_price": str(it["unit_price"]),
            "tax_rate": str(it.get("tax_rate", items[0]["tax_rate"])),
        }
        for it in items
    ]

    result = tool_dispatcher.execute_command(
        CreateInvoice,
        invoice_no=invoice_no,
        direction="in",
        invoice_type=arguments.get("invoice_type", "ordinary"),
        tax_rate=tax_rate,
        amount_without_tax=amount_without_tax,
        tax_amount=tax_amount,
        amount_with_tax=amount_with_tax,
        counterparty_name=supplier_name,
        issue_date=purchase_date,
        purchase_order_action="auto_create",
        items=invoice_items,
        notes=arguments.get("notes", ""),
    )
    return {
        "ok": True,
        "operation": "create_purchase_order_with_invoice",
        "result": _safe_serialize(result),
        "amount_with_tax": float(amount_with_tax),
        "tax_amount": float(tax_amount),
        "accounting_hint": (
            "发票驱动: 先开发票自动生成采购单。"
            "会计影响: 借:库存商品 借:应交税费-进项税额 贷:应付账款。"
            "小规模纳税人进项税不可抵扣, 含税全额入库存成本。"
        ),
    }


# ══════════════════════════════════════════════════════════════
# 9. 收款: create_receipt (客户收款, 银行流入)
# ══════════════════════════════════════════════════════════════
def create_receipt(arguments: dict) -> dict:
    """客户收款 (银行流入)。

    对应 sim helpers.create_customer_payment。
    调用路径: dispatch(CreateReceipt(data=ReceiptCreate(receipt_type='sale', ...)))
    会计影响: 借:1002 银行存款 贷:1122 应收账款。

    参数:
        sale_order_id: int  关联销售单 ID
        amount: float  收款金额
        payment_date: str  收款日期 (YYYY-MM-DD)
        bank_account_id: int  银行账户 ID (可选, 默认取首个)
        description: str  描述
    """
    from commands.cash_commands import CreateReceipt
    from schemas.receipt import ReceiptCreate

    sale_order_id = arguments.get("sale_order_id")
    amount = arguments.get("amount")
    payment_date_str = arguments.get("payment_date")

    if not sale_order_id:
        raise BusinessError(code=None, message="sale_order_id 必填")
    if amount is None or amount <= 0:
        raise BusinessError(code=None, message="amount 必填且必须 > 0")
    if not payment_date_str:
        raise BusinessError(code=None, message="payment_date 必填 (YYYY-MM-DD)")

    payment_date = _to_datetime(payment_date_str)

    data = ReceiptCreate(
        receipt_type="sale",
        related_entity_type="sale_order",
        related_entity_id=sale_order_id,
        amount=Decimal(str(amount)),
        receipt_method="company",
        receipt_date=payment_date,
        bank_account_id=arguments.get("bank_account_id"),
        description=arguments.get("description", ""),
    )

    result = tool_dispatcher.execute_command(CreateReceipt, data=data)
    return {
        "ok": True,
        "operation": "create_receipt",
        "result": _safe_serialize(result),
        "accounting_hint": "客户收款: 借:1002 银行存款 贷:1122 应收账款。",
    }


# ══════════════════════════════════════════════════════════════
# 10. 费用: create_expense (房租/水电等)
# ══════════════════════════════════════════════════════════════
def create_expense(arguments: dict) -> dict:
    """创建费用 (房租/水电/工资等)。

    对应 sim helpers.create_expense。
    调用路径: dispatch(CreateExpense(expense=ExpenseCreate(...)))
    会计影响: 借:6601 管理费用 (或 6602 销售/6603 财务) 贷:2202 应付账款/2241 其他应付款。

    参数:
        category: str  费用类别 (房租/水电/工资/材料/办公用品/运费/维修/税金及附加/所得税/其他)
        amount: float  金额
        expense_date: str  费用日期 (YYYY-MM-DD)
        description: str  描述
        functional_category: str  功能分类 (管理费用/销售费用/财务费用, 默认管理费用)
        payment_method: str  付款方式 (company/private_advance, 默认 company)
    """
    from commands.cash_commands import CreateExpense
    from schemas.expense import ExpenseCreate

    category = arguments.get("category")
    amount = arguments.get("amount")
    expense_date_str = arguments.get("expense_date")

    if not category:
        raise BusinessError(code=None, message="category 必填")
    if amount is None or amount <= 0:
        raise BusinessError(code=None, message="amount 必填且必须 > 0")
    if not expense_date_str:
        raise BusinessError(code=None, message="expense_date 必填 (YYYY-MM-DD)")

    expense_date = _to_datetime(expense_date_str)

    expense = ExpenseCreate(
        category=category,
        functional_category=arguments.get("functional_category", "管理费用"),
        amount=Decimal(str(amount)),
        expense_date=expense_date,
        payment_method=arguments.get("payment_method", "company"),
        description=arguments.get("description", ""),
    )

    result = tool_dispatcher.execute_command(CreateExpense, expense=expense)
    return {
        "ok": True,
        "operation": "create_expense",
        "result": _safe_serialize(result),
        "accounting_hint": (
            "费用入账: 借:6601 管理费用 (或 6602 销售/6603 财务) "
            "贷:2202 应付账款 (公司采购) / 2241 其他应付款 (个人垫付 private_advance)。"
            "铁律: 已过账 Expense 禁止直接删除, 必须通过 ReverseExpense 强制冲红。"
        ),
    }


# ══════════════════════════════════════════════════════════════
# 11. 银行: create_bank_entry (银行扣款/利息)
# ══════════════════════════════════════════════════════════════
def create_bank_entry(arguments: dict) -> dict:
    """银行扣款或利息收入。

    对应 sim helpers.create_bank_fee / create_bank_interest。
    调用路径: dispatch(CreateBankEntry(entry_type='bank_fee'/'interest_income', ...))

    参数:
        entry_type: str  类型 (bank_fee 银行扣款 / interest_income 利息收入)
        amount: float  金额
        transaction_date: str  交易日期 (YYYY-MM-DD)
        description: str  描述
        bank_account_id: int  银行账户 ID (可选)
    """
    from commands.bank_commands import CreateBankEntry

    entry_type = arguments.get("entry_type")
    amount = arguments.get("amount")
    transaction_date_str = arguments.get("transaction_date")

    if entry_type not in ("bank_fee", "interest_income"):
        raise BusinessError(
            code=None,
            message="entry_type 必须为 bank_fee (银行扣款) 或 interest_income (利息收入)",
        )
    if amount is None or amount <= 0:
        raise BusinessError(code=None, message="amount 必填且必须 > 0")
    if not transaction_date_str:
        raise BusinessError(code=None, message="transaction_date 必填 (YYYY-MM-DD)")

    result = tool_dispatcher.execute_command(
        CreateBankEntry,
        entry_type=entry_type,
        amount=float(amount),
        transaction_date=transaction_date_str,
        description=arguments.get("description", ""),
        bank_account_id=arguments.get("bank_account_id"),
    )
    hint = (
        "银行扣款: 借:6603 财务费用 贷:1002 银行存款。"
        if entry_type == "bank_fee"
        else "利息收入: 借:1002 银行存款 贷:6603 财务费用 (冲减财务费用, 不进 6301 营业外收入)。"
    )
    return {
        "ok": True,
        "operation": "create_bank_entry",
        "result": _safe_serialize(result),
        "accounting_hint": hint,
    }


# ══════════════════════════════════════════════════════════════
# 12-13. 固定资产: create_fixed_asset / batch_depreciate
# ══════════════════════════════════════════════════════════════
def create_fixed_asset(arguments: dict) -> dict:
    """创建固定资产。

    对应 sim helpers.create_fixed_asset_purchase。
    调用路径: create_fixed_asset(db, account_id, FixedAssetCreate(...), operator='ai')
    会计影响: 借:1601 固定资产 贷:2202 应付账款 (公司采购) / 2241 其他应付款 (个人垫付)。

    参数:
        name: str  资产名称
        cost: float  原值
        purchase_date: str  采购日期 (YYYY-MM-DD)
        useful_life: int  使用寿命 (月, 默认 60)
        salvage_rate: float  残值率 (默认 0.05)
        category: str  资产类别 (默认电子设备)
        notes: str  备注 (用于生成 asset_code)
    """
    from schemas.finance import FixedAssetCreate
    from crud.finance.fixed_assets import create_fixed_asset as _create_fa

    name = arguments.get("name")
    cost = arguments.get("cost")
    purchase_date_str = arguments.get("purchase_date")

    if not name:
        raise BusinessError(code=None, message="name 必填")
    if cost is None or cost <= 0:
        raise BusinessError(code=None, message="cost 必填且必须 > 0")
    if not purchase_date_str:
        raise BusinessError(code=None, message="purchase_date 必填 (YYYY-MM-DD)")

    purchase_date = _parse_date(purchase_date_str)
    asset_code = f"FA-{purchase_date.strftime('%Y%m%d')}-{name[:6]}"

    data = FixedAssetCreate(
        asset_code=asset_code,
        name=name,
        category=arguments.get("category", "电子设备"),
        original_value=Decimal(str(cost)),
        salvage_rate=Decimal(str(arguments.get("salvage_rate", 0.05))),
        useful_life=arguments.get("useful_life", 60),
        depreciation_method="年限平均法",
        start_date=purchase_date_str,
        status="在用",
    )

    # create_fixed_asset 是直接函数调用 (非 Command), 需要手动开写权限
    from database import SessionLocal, _request_write_perm
    account_id = account_context.require_account_id()
    db = SessionLocal()
    token = _request_write_perm.set(True)
    try:
        asset = _create_fa(db, account_id, data, operator="ai")
        db.commit()
        return {
            "ok": True,
            "operation": "create_fixed_asset",
            "result": _safe_serialize(asset),
            "accounting_hint": (
                "固定资产入账: 借:1601 固定资产 贷:2202 应付账款 (公司采购) / "
                "2241 其他应付款 (个人垫付 private_advance)。"
                "次月起按月计提折旧: 借:6601/6602 管理费用/销售费用 贷:1602 累计折旧。"
            ),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        _request_write_perm.reset(token)
        db.close()


def batch_depreciate(arguments: dict) -> dict:
    """批量计提折旧。

    对应 sim reset_and_run_all.run_month_close 第 1 步。
    调用路径: dispatch(BatchDepreciateFixedAssets(period=...))
    会计影响: 借:6601/6602 管理费用/销售费用 贷:1602 累计折旧。

    参数:
        period: str  目标月份 (YYYY-MM)
    """
    from commands.fixed_asset_commands import BatchDepreciateFixedAssets

    period = arguments.get("period")
    if not period:
        raise BusinessError(code=None, message="period 必填 (YYYY-MM)")

    result = tool_dispatcher.execute_command(BatchDepreciateFixedAssets, period=period)
    return {
        "ok": True,
        "operation": "batch_depreciate",
        "period": period,
        "result": _safe_serialize(result),
        "accounting_hint": "月度折旧计提: 借:6601/6602 管理费用/销售费用 贷:1602 累计折旧。",
    }


# ══════════════════════════════════════════════════════════════
# 14-15. 税务申报: declare_vat / declare_surcharge
# ══════════════════════════════════════════════════════════════
def declare_vat(arguments: dict) -> dict:
    """提交增值税申报。

    对应 sim run_declarations_and_validate.submit_declarations 的 VAT 部分。
    调用路径: dispatch(DeclareVAT(period=..., taxpayer_type=...))

    期间格式:
    - 小规模纳税人: YYYY-QQ (如 2026-Q2), 按季度申报
    - 一般纳税人: YYYY-MM (如 2026-06), 按月申报

    参数:
        period: str  申报期间 (格式随纳税人类型变化)
        taxpayer_type: str  纳税人类型 (small_scale/general, 空则从 Account 读取)
    """
    from commands.tax_declaration_commands import DeclareVAT

    period = arguments.get("period")
    if not period:
        raise BusinessError(code=None, message="period 必填")

    # 从 Account 取默认纳税人类型 (与 sim 一致)
    if not arguments.get("taxpayer_type"):
        def _get_taxpayer(db, aid):
            import models
            acc = db.query(models.Account).filter(models.Account.id == aid).first()
            return acc.taxpayer_type_l3 if acc else "small_scale"
        taxpayer_type = tool_dispatcher.run_readonly(_get_taxpayer)
    else:
        taxpayer_type = arguments["taxpayer_type"]

    result = tool_dispatcher.execute_command(
        DeclareVAT,
        period=period,
        taxpayer_type=taxpayer_type,
    )
    return {
        "ok": True,
        "operation": "declare_vat",
        "period": period,
        "taxpayer_type": taxpayer_type,
        "result": _safe_serialize(result),
        "accounting_hint": (
            "VAT 申报: 发票是销项税真相源 (BR-1, BR-27), 申报金额 = 发票汇总税额。"
            "小规模季度销售额 ≤30 万普票免征, 6% 减按 1% 征收 (2023-2027 政策)。"
            "增值税申报删除前必须调用 reverse_journal('vat_transfer_out', declaration_id, force=True)。"
        ),
    }


def declare_surcharge(arguments: dict) -> dict:
    """提交附加税申报 (城建税/教育费附加/地方教育附加)。

    对应 sim run_declarations_and_validate.submit_declarations 的 Surcharge 部分。
    调用路径: dispatch(DeclareSurcharge(period=..., urban_construction_tax=..., ...))

    附加税随增值税申报周期: 小规模按季度, 一般纳税人按月。
    城建税享受六税两费减半, 教育费附加/地方教育附加季度销售额 ≤30 万免征 (财税〔2016〕12号)。

    参数:
        period: str  申报期间 (与 VAT 期间一致)
        urban_construction_tax: float  城建税金额
        education_surcharge: float  教育费附加金额
        local_education_surcharge: float  地方教育附加金额
        notes: str  备注
    """
    from commands.tax_declaration_commands import DeclareSurcharge

    period = arguments.get("period")
    if not period:
        raise BusinessError(code=None, message="period 必填")

    result = tool_dispatcher.execute_command(
        DeclareSurcharge,
        period=period,
        urban_construction_tax=Decimal(str(arguments.get("urban_construction_tax", 0))),
        education_surcharge=Decimal(str(arguments.get("education_surcharge", 0))),
        local_education_surcharge=Decimal(str(arguments.get("local_education_surcharge", 0))),
        notes=arguments.get("notes", ""),
    )
    return {
        "ok": True,
        "operation": "declare_surcharge",
        "period": period,
        "result": _safe_serialize(result),
        "accounting_hint": (
            "附加税申报: 借:6403 税金及附加 贷:222101 应交税费-城建税 / "
            "222102 教育费附加 / 222110 地方教育附加。"
            "城建税享受六税两费减半; 教育费附加/地方教育附加季度销售额 ≤30 万免征。"
        ),
    }


# ══════════════════════════════════════════════════════════════
# 16. 月结: month_end_close
# ══════════════════════════════════════════════════════════════
def month_end_close(arguments: dict) -> dict:
    """月结 (折旧→算税→结转损益→年结→税务核对, 5 步自动执行)。

    对应 sim reset_and_run_all.run_month_close。
    调用路径: dispatch(MonthEndClose(period=..., taxpayer_type=...))
    12 月会额外执行年结 (4103 → 4104 未分配利润)。

    参数:
        period: str  目标月份 (YYYY-MM)
        taxpayer_type: str  纳税人类型 (空则从 Account 读取)
    """
    from commands.month_end import MonthEndClose

    period = arguments.get("period")
    if not period:
        raise BusinessError(code=None, message="period 必填 (YYYY-MM)")

    result = tool_dispatcher.execute_command(
        MonthEndClose,
        period=period,
        taxpayer_type=arguments.get("taxpayer_type", ""),
    )
    return {
        "ok": True,
        "operation": "month_end_close",
        "period": period,
        "result": _safe_serialize(result),
        "accounting_hint": (
            "月结 5 步: (1) 折旧/摊销计提 (2) 增值税+附加税+所得税计提 "
            "(3) 损益结转到 4103 本年利润 (4) 12月年结 4103→4104 未分配利润 "
            "(5) 税务核对 8 项。"
            "铁律: 已过账凭证禁止删除, 错误必须走红冲流程。"
        ),
    }


# ══════════════════════════════════════════════════════════════
# 17-18. 报表: get_balance_sheet / get_income_statement
# ══════════════════════════════════════════════════════════════
def get_balance_sheet(arguments: dict) -> dict:
    """查询资产负债表 (带 trace 追溯链, 只读)。

    对应 sim run_declarations_and_validate.run_validation 的 BS 部分。
    调用路径: ReportEngine().execute(BALANCE_SHEET, sn, trace=True, source_mode='invoice')

    参数:
        date: str  报表日期 (YYYY-MM-DD)
        reconcile: bool  是否返回双路径对账结果 (默认 false)
    """
    from database import SessionLocal
    from crud.finance._snapshot import LedgerSnapshot
    from reports.engine import ReportEngine
    from reports.definitions.balance_sheet import BALANCE_SHEET
    from reports.reconcile import ReportReconciliation
    from utils import end_of_day

    date_str = arguments.get("date")
    if not date_str:
        raise BusinessError(code=None, message="date 必填 (YYYY-MM-DD)")
    reconcile = arguments.get("reconcile", False)

    account_id = account_context.require_account_id()
    qd = end_of_day(datetime.strptime(date_str, "%Y-%m-%d"))

    db = SessionLocal()
    try:
        sn = LedgerSnapshot(db, account_id, bs_cutoff=qd)
        engine = ReportEngine()
        result = engine.execute(BALANCE_SHEET, sn, trace=True, source_mode="invoice")
        out = {"ok": True, "date": date_str, "account_id": account_id, "balance_sheet": result}
        if reconcile:
            recon = ReportReconciliation(db, sn, report_type="balance_sheet")
            recon_values = _extract_values(result)
            out["reconciliation"] = recon.reconcile(
                BALANCE_SHEET, recon_values, source_mode="invoice"
            ).to_dict()
        return out
    finally:
        db.close()


def get_income_statement(arguments: dict) -> dict:
    """查询利润表 (带 trace 追溯链, 只读)。

    对应 sim run_declarations_and_validate.run_validation 的 IS 部分。
    调用路径: ReportEngine().execute(INCOME_STATEMENT, sn, trace=True)

    参数:
        start_date: str  开始日期 (YYYY-MM-DD)
        end_date: str  结束日期 (YYYY-MM-DD)
        reconcile: bool  是否返回对账结果 (默认 false)
    """
    from database import SessionLocal
    from crud.finance._snapshot import LedgerSnapshot
    from reports.engine import ReportEngine
    from reports.definitions.income_statement import INCOME_STATEMENT
    from reports.reconcile import ReportReconciliation
    from utils import end_of_day

    start_str = arguments.get("start_date")
    end_str = arguments.get("end_date")
    if not start_str or not end_str:
        raise BusinessError(code=None, message="start_date 和 end_date 必填 (YYYY-MM-DD)")
    reconcile = arguments.get("reconcile", False)

    account_id = account_context.require_account_id()
    sd = datetime.strptime(start_str, "%Y-%m-%d")
    ed = end_of_day(datetime.strptime(end_str, "%Y-%m-%d"))

    db = SessionLocal()
    try:
        sn = LedgerSnapshot(db, account_id, bs_cutoff=ed, period_start=sd, period_end=ed)
        engine = ReportEngine()
        result = engine.execute(INCOME_STATEMENT, sn, trace=True)
        out = {"ok": True, "start_date": start_str, "end_date": end_str, "account_id": account_id, "income_statement": result}
        if reconcile:
            recon = ReportReconciliation(db, sn, report_type="income_statement")
            recon_values = _extract_values(result)
            out["reconciliation"] = recon.reconcile(INCOME_STATEMENT, recon_values).to_dict()
        return out
    finally:
        db.close()


def _extract_values(result: dict) -> dict:
    """从 trace 结果提取 {key: value} 用于对账。"""
    out = {}
    for k, v in result.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and "value" in v:
            out[k] = v["value"]
        elif isinstance(v, (int, float)):
            out[k] = v
    return out


# ══════════════════════════════════════════════════════════════
# Tool 清单 (供 server.py 注册)
# ══════════════════════════════════════════════════════════════
TOOL_TEMPLATES = [
    # ── 1. 上下文 ──
    {
        "name": "set_current_account",
        "description": (
            "设置当前操作的账本上下文。MCP server 启动时已自动选默认账本, "
            "切换账本时调用此工具。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "integer", "description": "目标账本 ID"},
            },
            "required": ["account_id"],
        },
    },
    # ── 2. 基础数据 ──
    {
        "name": "setup_basic_data",
        "description": (
            "建立基础数据 (商品/客户/供应商/银行账户)。"
            "商品 track_inventory 决定会计科目: True→1405 库存, False→6601 费用。"
            "不生成会计凭证, 仅建立主数据。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "products": {
                    "type": "array",
                    "description": "商品列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "sku": {"type": "string"},
                            "category": {"type": "string", "description": "商品/服务"},
                            "unit": {"type": "string"},
                            "track_inventory": {"type": "boolean", "description": "是否跟踪库存"},
                        },
                    },
                },
                "customers": {"type": "array", "items": {"type": "string"}, "description": "客户名称列表"},
                "suppliers": {"type": "array", "items": {"type": "string"}, "description": "供应商名称列表"},
                "bank_account": {
                    "type": "object",
                    "properties": {
                        "bank_name": {"type": "string"},
                        "account_number": {"type": "string"},
                    },
                },
            },
        },
    },
    {
        "name": "list_products",
        "description": "列出当前账本所有商品 (含 track_inventory 标志)。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_customers",
        "description": "列出当前账本所有客户。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_suppliers",
        "description": "列出当前账本所有供应商。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_bank_accounts",
        "description": "列出当前账本所有银行账户。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # ── 3. 销售 ──
    {
        "name": "create_sale_order_with_invoice",
        "description": (
            "创建销售单 (发票驱动: 先开发票自动生成销售单)。"
            "调用路径: CreateInvoice(direction='out', sale_order_action='auto_create')。"
            "会计影响: 借:应收账款 贷:主营业务收入+应交税费-销项税额; "
            "同时借:主营业务成本 贷:库存商品 (实物商品, 按 unit_cost 加权平均)。"
            "铁律: 发票是销项税真相源; COGS 必须用 SaleItem.unit_cost。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "sale_date": {"type": "string", "description": "YYYY-MM-DD"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number", "description": "含税单价"},
                            "tax_rate": {"type": "string", "description": "如 0.01 / 0.06"},
                            "notes": {"type": "string"},
                        },
                    },
                },
                "invoice_type": {"type": "string", "default": "ordinary"},
                "notes": {"type": "string"},
            },
            "required": ["customer_name", "sale_date", "items"],
        },
    },
    {
        "name": "create_receipt",
        "description": (
            "客户收款 (银行流入)。"
            "会计影响: 借:1002 银行存款 贷:1122 应收账款。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sale_order_id": {"type": "integer"},
                "amount": {"type": "number"},
                "payment_date": {"type": "string", "description": "YYYY-MM-DD"},
                "bank_account_id": {"type": "integer"},
                "description": {"type": "string"},
            },
            "required": ["sale_order_id", "amount", "payment_date"],
        },
    },
    # ── 4. 采购 ──
    {
        "name": "create_purchase_order_with_invoice",
        "description": (
            "创建采购单 (发票驱动: 先开发票自动生成采购单)。"
            "调用路径: CreateInvoice(direction='in', purchase_order_action='auto_create')。"
            "会计影响: 借:库存商品 借:应交税费-进项税额 贷:应付账款。"
            "小规模纳税人进项税不可抵扣, 含税全额入库存成本。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier_name": {"type": "string"},
                "purchase_date": {"type": "string", "description": "YYYY-MM-DD"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number", "description": "含税单价"},
                            "tax_rate": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                    },
                },
                "invoice_type": {"type": "string", "default": "ordinary"},
                "notes": {"type": "string"},
            },
            "required": ["supplier_name", "purchase_date", "items"],
        },
    },
    # ── 5. 费用 ──
    {
        "name": "create_expense",
        "description": (
            "创建费用 (房租/水电/工资等)。"
            "会计影响: 借:6601 管理费用 贷:2202 应付账款 / 2241 其他应付款 (个人垫付)。"
            "铁律: 已过账 Expense 禁止直接删除, 必须通过 ReverseExpense 强制冲红。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["房租", "水电", "工资", "材料", "办公用品", "运费", "维修", "税金及附加", "所得税", "其他"]},
                "amount": {"type": "number"},
                "expense_date": {"type": "string", "description": "YYYY-MM-DD"},
                "description": {"type": "string"},
                "functional_category": {"type": "string", "enum": ["管理费用", "销售费用", "财务费用"], "default": "管理费用"},
                "payment_method": {"type": "string", "enum": ["company", "private_advance"], "default": "company"},
            },
            "required": ["category", "amount", "expense_date"],
        },
    },
    # ── 6. 银行 ──
    {
        "name": "create_bank_entry",
        "description": (
            "银行扣款或利息收入。"
            "bank_fee: 借:6603 财务费用 贷:1002 银行存款; "
            "interest_income: 借:1002 银行存款 贷:6603 财务费用 (冲减财务费用, 不进 6301)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_type": {"type": "string", "enum": ["bank_fee", "interest_income"]},
                "amount": {"type": "number"},
                "transaction_date": {"type": "string", "description": "YYYY-MM-DD"},
                "description": {"type": "string"},
                "bank_account_id": {"type": "integer"},
            },
            "required": ["entry_type", "amount", "transaction_date"],
        },
    },
    # ── 7. 固定资产 ──
    {
        "name": "create_fixed_asset",
        "description": (
            "创建固定资产。"
            "会计影响: 借:1601 固定资产 贷:2202 应付账款 / 2241 其他应付款 (个人垫付)。"
            "次月起按月计提折旧: 借:6601/6602 贷:1602 累计折旧。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "cost": {"type": "number"},
                "purchase_date": {"type": "string", "description": "YYYY-MM-DD"},
                "useful_life": {"type": "integer", "default": 60, "description": "使用寿命(月)"},
                "salvage_rate": {"type": "number", "default": 0.05},
                "category": {"type": "string", "default": "电子设备"},
                "notes": {"type": "string"},
            },
            "required": ["name", "cost", "purchase_date"],
        },
    },
    {
        "name": "batch_depreciate",
        "description": (
            "批量计提折旧。"
            "会计影响: 借:6601/6602 管理费用/销售费用 贷:1602 累计折旧。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "YYYY-MM"},
            },
            "required": ["period"],
        },
    },
    # ── 8. 税务申报 ──
    {
        "name": "declare_vat",
        "description": (
            "提交增值税申报。"
            "期间格式: 小规模 YYYY-QQ (按季), 一般纳税人 YYYY-MM (按月)。"
            "发票是销项税真相源, 申报金额 = 发票汇总税额。"
            "小规模季度销售额 ≤30 万普票免征, 6% 减按 1% 征收 (2023-2027 政策)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "小规模 YYYY-QQ / 一般纳税人 YYYY-MM"},
                "taxpayer_type": {"type": "string", "enum": ["small_scale", "general"], "description": "空则从 Account 读取"},
            },
            "required": ["period"],
        },
    },
    {
        "name": "declare_surcharge",
        "description": (
            "提交附加税申报 (城建税/教育费附加/地方教育附加)。"
            "附加税随增值税申报周期: 小规模按季, 一般纳税人按月。"
            "城建税享受六税两费减半; 教育费附加/地方教育附加季度销售额 ≤30 万免征。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string"},
                "urban_construction_tax": {"type": "number", "default": 0},
                "education_surcharge": {"type": "number", "default": 0},
                "local_education_surcharge": {"type": "number", "default": 0},
                "notes": {"type": "string"},
            },
            "required": ["period"],
        },
    },
    # ── 9. 月结 ──
    {
        "name": "month_end_close",
        "description": (
            "月结 (折旧→算税→结转损益→年结→税务核对, 5 步自动执行)。"
            "12 月会额外执行年结 (4103 → 4104 未分配利润)。"
            "铁律: 已过账凭证禁止删除, 错误必须走红冲流程。"
            "危险等级: 高 (会生成大量凭证)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "YYYY-MM"},
                "taxpayer_type": {"type": "string"},
            },
            "required": ["period"],
        },
    },
    # ── 10. 报表 ──
    {
        "name": "get_balance_sheet",
        "description": (
            "查询资产负债表 (会小企01表), 默认带 trace 追溯链。"
            "字段的 contributions 会列出构成来源 (凭证/发票/库存流水)。"
            "只读, 不修改数据。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "reconcile": {"type": "boolean", "default": False},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_income_statement",
        "description": (
            "查询利润表 (会小企02表), 默认带 trace 追溯链。"
            "只读, 不修改数据。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "reconcile": {"type": "boolean", "default": False},
            },
            "required": ["start_date", "end_date"],
        },
    },
]

# Tool 名 → 实现函数映射
TOOL_HANDLERS = {
    "set_current_account": set_current_account,
    "setup_basic_data": setup_basic_data,
    "list_products": list_products,
    "list_customers": list_customers,
    "list_suppliers": list_suppliers,
    "list_bank_accounts": list_bank_accounts,
    "create_sale_order_with_invoice": create_sale_order_with_invoice,
    "create_receipt": create_receipt,
    "create_purchase_order_with_invoice": create_purchase_order_with_invoice,
    "create_expense": create_expense,
    "create_bank_entry": create_bank_entry,
    "create_fixed_asset": create_fixed_asset,
    "batch_depreciate": batch_depreciate,
    "declare_vat": declare_vat,
    "declare_surcharge": declare_surcharge,
    "month_end_close": month_end_close,
    "get_balance_sheet": get_balance_sheet,
    "get_income_statement": get_income_statement,
}
