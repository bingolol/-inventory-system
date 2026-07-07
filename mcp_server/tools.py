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


def _validate_period_by_taxpayer(period: str, tool_name: str = "") -> str:
    """校验 period 格式与当前账本纳税人类型匹配。

    小规模按季度: YYYY-QQ (如 2026-Q2)
    一般纳税人按月: YYYY-MM (如 2026-06)
    月结 period 总是 YYYY-MM (与纳税人类型无关)

    返回: taxpayer_type
    抛 BusinessError: 格式不匹配
    """
    if not period:
        raise BusinessError(code=None, message=f"{tool_name}: period 必填")

    def _get_taxpayer(db, aid):
        import models
        acc = db.query(models.Account).filter(models.Account.id == aid).first()
        return acc.taxpayer_type_l3 if acc else "small_scale"

    taxpayer_type = tool_dispatcher.run_readonly(_get_taxpayer)

    if tool_name == "month_end_close":
        # 月结总是 YYYY-MM
        if not (len(period) == 7 and period[:4].isdigit() and period[4] == "-" and period[5:7].isdigit()):
            raise BusinessError(
                code=None,
                message=f"{tool_name}: period 格式必须是 YYYY-MM (如 2026-07), 收到: {period}",
            )
    elif tool_name in ("declare_vat", "declare_surcharge"):
        if taxpayer_type == "small_scale":
            # YYYY-QQ
            ok = (len(period) == 7 and period[:4].isdigit() and period[4] == "-"
                  and period[5] == "Q" and period[6].isdigit() and 1 <= int(period[6]) <= 4)
            if not ok:
                raise BusinessError(
                    code=None,
                    message=f"{tool_name}: 小规模纳税人 period 格式必须是 YYYY-QQ (如 2026-Q2), 收到: {period}",
                )
        else:
            # YYYY-MM
            ok = (len(period) == 7 and period[:4].isdigit() and period[4] == "-"
                  and period[5:7].isdigit() and 1 <= int(period[5:7]) <= 12)
            if not ok:
                raise BusinessError(
                    code=None,
                    message=f"{tool_name}: 一般纳税人 period 格式必须是 YYYY-MM (如 2026-06), 收到: {period}",
                )
    return taxpayer_type


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
    # 提取关联销售单 ID (invoice.related_order_id), 让 agent 一眼能看到
    sale_order_id = getattr(result, "related_order_id", None) if result else None
    invoice_id = getattr(result, "id", None) if result else None
    return {
        "ok": True,
        "operation": "create_sale_order_with_invoice",
        "result": _safe_serialize(result),
        "invoice_id": invoice_id,
        "sale_order_id": sale_order_id,
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
    # 提取关联采购单 ID (invoice.related_order_id), 让 agent 一眼能看到
    purchase_order_id = getattr(result, "related_order_id", None) if result else None
    invoice_id = getattr(result, "id", None) if result else None
    return {
        "ok": True,
        "operation": "create_purchase_order_with_invoice",
        "result": _safe_serialize(result),
        "invoice_id": invoice_id,
        "purchase_order_id": purchase_order_id,
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
    # 校验 period 格式与纳税人类型匹配 (小规模 YYYY-QQ / 一般纳税人 YYYY-MM)
    taxpayer_type = _validate_period_by_taxpayer(period, tool_name="declare_vat")
    if arguments.get("taxpayer_type"):
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

    附加税申报是 L1 外部输入 (用户实际要交多少税), 不是系统派生值。
    月结时 engine_tax.calculate_surcharges() 会基于已申报 VAT 自动计提附加税凭证 (L3 派生),
    但申报本身必须由用户根据税务局实际通知的金额录入。

    附加税随增值税申报周期: 小规模按季度, 一般纳税人按月。
    城建税享受六税两费减半, 教育费附加/地方教育附加季度销售额 ≤30 万免征 (财税〔2016〕12号)。
    agent 应提示用户: 这些免征/减半规则已由月结自动处理, 这里只需录用户实际申报的金额。

    参数:
        period: str  申报期间 (与 VAT 期间一致)
        urban_construction_tax: float  城建税金额 (用户从税务局申报表抄录)
        education_surcharge: float  教育费附加金额
        local_education_surcharge: float  地方教育附加金额
        notes: str  备注
    """
    from commands.tax_declaration_commands import DeclareSurcharge

    period = arguments.get("period")
    # 校验 period 格式与纳税人类型匹配 (小规模 YYYY-QQ / 一般纳税人 YYYY-MM)
    _validate_period_by_taxpayer(period, tool_name="declare_surcharge")

    urban = arguments.get("urban_construction_tax")
    edu = arguments.get("education_surcharge")
    local_edu = arguments.get("local_education_surcharge")
    if urban is None or edu is None or local_edu is None:
        raise BusinessError(
            code=None,
            message="附加税是 L1 用户输入: urban_construction_tax / education_surcharge / "
                    "local_education_surcharge 三个金额必须由用户提供 (从税务局申报表抄录)",
        )

    result = tool_dispatcher.execute_command(
        DeclareSurcharge,
        period=period,
        urban_construction_tax=Decimal(str(urban)),
        education_surcharge=Decimal(str(edu)),
        local_education_surcharge=Decimal(str(local_edu)),
        notes=arguments.get("notes", ""),
    )
    return {
        "ok": True,
        "operation": "declare_surcharge",
        "period": period,
        "result": _safe_serialize(result),
        "accounting_hint": (
            "附加税申报 (L1 用户输入): 借:6403 税金及附加 贷:222101/222102/222110。"
            "金额来自用户从税务局申报表抄录的实际申报值, 不是系统派生。"
            "月结时 engine_tax 会用 calculate_surcharges 自动计提, 此处仅录入申报值。"
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
    # 校验 period 格式 (月结总是 YYYY-MM)
    _validate_period_by_taxpayer(period, tool_name="month_end_close")

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
    reconcile = arguments.get("reconcile", True)

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
    reconcile = arguments.get("reconcile", True)

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
# 19-22. 历史查询 (只读, agent 解释报表/回答用户疑问时用)
# ══════════════════════════════════════════════════════════════
def list_invoices(arguments: dict) -> dict:
    """查询发票列表 (只读)。

    支持按 direction / 日期范围 / 购销方名称过滤。
    发票是 VAT 真相源, agent 解释"上个月开了多少票"时用。

    参数:
        direction: str  方向过滤 (out 销项 / in 进项, 空则全部)
        date_from: str  起始日期 (YYYY-MM-DD, 含, 空 则不限)
        date_to: str  结束日期 (YYYY-MM-DD, 含, 空 则不限)
        counterparty_name: str  购销方名称模糊匹配 (空则不过滤)
        limit: int  最多返回条数 (默认 100, 上限 500)
    """
    direction = arguments.get("direction")
    date_from = arguments.get("date_from")
    date_to = arguments.get("date_to")
    counterparty_name = arguments.get("counterparty_name")
    limit = min(int(arguments.get("limit", 100)), 500)

    def _query(db, aid):
        import models
        from datetime import timedelta
        q = db.query(models.Invoice).filter(models.Invoice.account_id == aid)
        if direction in ("out", "in"):
            q = q.filter(models.Invoice.direction == direction)
        if date_from:
            q = q.filter(models.Invoice.issue_date_l1 >= _parse_date(date_from))
        if date_to:
            # issue_date_l1 在 SQLite 存为 datetime 字符串, 用 < next_day 避免
            # '2026-07-07 00:00:00.000000' > '2026-07-07' 的字符串比较问题
            q = q.filter(models.Invoice.issue_date_l1 < _parse_date(date_to) + timedelta(days=1))
        if counterparty_name:
            q = q.filter(models.Invoice.counterparty_name.like(f"%{counterparty_name}%"))
        items = q.order_by(models.Invoice.issue_date_l1.desc()).limit(limit).all()
        return [{
            "id": inv.id,
            "invoice_no": inv.invoice_no,
            "direction": inv.direction,
            "invoice_type": inv.invoice_type,
            "amount_without_tax": float(inv.amount_without_tax_l1) if inv.amount_without_tax_l1 else 0,
            "tax_amount": float(inv.tax_amount_l1) if inv.tax_amount_l1 else 0,
            "amount_with_tax": float(inv.amount_with_tax_l1) if inv.amount_with_tax_l1 else 0,
            "tax_rate": float(inv.tax_rate_l1) if inv.tax_rate_l1 else 0,
            "counterparty_name": inv.counterparty_name,
            "issue_date": inv.issue_date_l1.isoformat() if inv.issue_date_l1 else None,
            "is_reversed": inv.is_reversed,
            "related_order_id": inv.related_order_id,
            "related_order_type": inv.related_order_type,
        } for inv in items]

    return {"ok": True, "invoices": tool_dispatcher.run_readonly(_query)}


def get_sale_order(arguments: dict) -> dict:
    """查询销售单详情 (含 items + 关联发票 + 收款状态, 只读)。

    agent 回答"那笔 1500 元的销售单怎么回事"时用。

    参数:
        order_id: int  销售单 ID
    """
    order_id = arguments.get("order_id")
    if not order_id:
        raise BusinessError(code=None, message="order_id 必填")

    def _query(db, aid):
        import models
        order = db.query(models.SaleOrder).filter(
            models.SaleOrder.account_id == aid,
            models.SaleOrder.id == order_id,
        ).first()
        if not order:
            return {"order": None, "error": f"销售单 {order_id} 不存在"}

        items = [{
            "id": it.id,
            "product_id": it.product_id,
            "product_name": it.product.name if it.product else None,
            "quantity": float(it.quantity_l1),
            "unit_price": float(it.unit_price_l1),
            "tax_rate": float(it.tax_rate_l1) if it.tax_rate_l1 else 0,
            "notes": it.notes,
        } for it in (order.items or [])]

        # 关联发票
        invoices = db.query(models.Invoice).filter(
            models.Invoice.related_order_id == order.id,
            models.Invoice.related_order_type == "sale_order",
            models.Invoice.account_id == aid,
        ).all()
        inv_data = [{
            "id": inv.id, "invoice_no": inv.invoice_no,
            "direction": inv.direction, "invoice_type": inv.invoice_type,
            "amount_with_tax": float(inv.amount_with_tax_l1) if inv.amount_with_tax_l1 else 0,
            "issue_date": inv.issue_date_l1.isoformat() if inv.issue_date_l1 else None,
            "is_reversed": inv.is_reversed,
        } for inv in invoices]

        # 收款记录
        receipts = db.query(models.Receipt).filter(
            models.Receipt.related_entity_type == "sale_order",
            models.Receipt.related_entity_id == order.id,
            models.Receipt.account_id == aid,
        ).all()
        rcpt_data = [{
            "id": r.id, "amount": float(r.amount_l1) if r.amount_l1 else 0,
            "receipt_date": r.receipt_date_l1.isoformat() if r.receipt_date_l1 else None,
            "is_reversed": getattr(r, "is_reversed", False),
        } for r in receipts]

        return {
            "order": {
                "id": order.id, "order_no": order.order_no,
                "customer_id": order.customer_id,
                "customer_name": order.customer.name if order.customer else None,
                "total_price": float(order.total_price_l1) if order.total_price_l1 else 0,
                "payment_status": order.payment_status,
                "status": order.status,
                "sale_date": order.sale_date_l1.isoformat() if order.sale_date_l1 else None,
                "notes": order.notes,
            },
            "items": items,
            "invoices": inv_data,
            "receipts": rcpt_data,
        }

    return {"ok": True, **tool_dispatcher.run_readonly(_query)}


def get_purchase_order(arguments: dict) -> dict:
    """查询采购单详情 (含 items + 关联发票, 只读)。

    参数:
        order_id: int  采购单 ID
    """
    order_id = arguments.get("order_id")
    if not order_id:
        raise BusinessError(code=None, message="order_id 必填")

    def _query(db, aid):
        import models
        order = db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.account_id == aid,
            models.PurchaseOrder.id == order_id,
        ).first()
        if not order:
            return {"order": None, "error": f"采购单 {order_id} 不存在"}

        items = [{
            "id": it.id,
            "product_id": it.product_id,
            "product_name": it.product.name if it.product else None,
            "quantity": float(it.quantity_l1),
            "unit_price": float(it.unit_price_l1),
            "tax_rate": float(it.tax_rate_l1) if it.tax_rate_l1 else 0,
        } for it in (order.items or [])]

        invoices = db.query(models.Invoice).filter(
            models.Invoice.related_order_id == order.id,
            models.Invoice.related_order_type == "purchase_order",
            models.Invoice.account_id == aid,
        ).all()
        inv_data = [{
            "id": inv.id, "invoice_no": inv.invoice_no,
            "amount_with_tax": float(inv.amount_with_tax_l1) if inv.amount_with_tax_l1 else 0,
            "issue_date": inv.issue_date_l1.isoformat() if inv.issue_date_l1 else None,
            "is_reversed": inv.is_reversed,
        } for inv in invoices]

        return {
            "order": {
                "id": order.id, "order_no": order.order_no,
                "supplier_id": order.supplier_id,
                "supplier_name": order.supplier.name if order.supplier else None,
                "total_price": float(order.total_price_l1) if order.total_price_l1 else 0,
                "payment_status": order.payment_status,
                "status": order.status,
                "purchase_date": order.purchase_date_l1.isoformat() if order.purchase_date_l1 else None,
            },
            "items": items,
            "invoices": inv_data,
        }

    return {"ok": True, **tool_dispatcher.run_readonly(_query)}


def list_journal_entries(arguments: dict) -> dict:
    """查询会计凭证分录 (只读)。

    agent 解释报表项目时, 用此 tool 拿到构成报表的底层凭证。
    支持按日期范围 / move_type / source_model 过滤。

    参数:
        date_from: str  起始日期 (YYYY-MM-DD, 含)
        date_to: str  结束日期 (YYYY-MM-DD, 含)
        move_type: str  凭证类型 (sale_order/purchase_order/receipt/payment/expense/...)
        source_model: str  来源模型 (sale_order/purchase_order/expense/fixed_asset/...)
        limit: int  最多返回条数 (默认 100, 上限 500)
    """
    date_from = arguments.get("date_from")
    date_to = arguments.get("date_to")
    move_type = arguments.get("move_type")
    source_model = arguments.get("source_model")
    limit = min(int(arguments.get("limit", 100)), 500)

    def _query(db, aid):
        import models
        from models_finance import AccountMove, AccountMoveLine, Ledger
        import models as _m
        acc = db.query(_m.Account).filter(_m.Account.id == aid).first()
        if not acc:
            return []
        ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
        if not ledger:
            return []
        q = db.query(AccountMove).filter(AccountMove.ledger_id == ledger.id)
        if date_from:
            q = q.filter(AccountMove.date_l1 >= _parse_date(date_from))
        if date_to:
            q = q.filter(AccountMove.date_l1 <= _parse_date(date_to))
        if move_type:
            q = q.filter(AccountMove.move_type == move_type)
        if source_model:
            q = q.filter(AccountMove.source_model == source_model)
        q = q.filter(AccountMove.state == "posted")
        moves = q.order_by(AccountMove.date_l1.desc()).limit(limit).all()

        out = []
        for m in moves:
            lines = db.query(AccountMoveLine).filter(
                AccountMoveLine.move_id == m.id
            ).all()
            out.append({
                "id": m.id,
                "date": m.date_l1.isoformat() if m.date_l1 else None,
                "move_type": m.move_type,
                "source_model": m.source_model,
                "source_id": m.source_id,
                "state": m.state,
                "is_reversal": getattr(m, "is_reversal", False),
                "lines": [{
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "debit": float(line.debit_l2) if line.debit_l2 else 0,
                    "credit": float(line.credit_l2) if line.credit_l2 else 0,
                } for line in lines],
            })
        return out

    return {"ok": True, "entries": tool_dispatcher.run_readonly(_query)}


# ══════════════════════════════════════════════════════════════
# 23-26. 红冲 (写操作, agent 引导用户修正错误时用)
# ══════════════════════════════════════════════════════════════
def reverse_invoice(arguments: dict) -> dict:
    """红字发票冲红 (写操作, 危险)。

    调用路径: dispatch(ReverseInvoice(invoice_id, reason))
    会级联冲红关联的 expense 凭证, 标记原发票 is_reversed=True。
    铁律: 已申报 VAT 的发票冲红后, 必须重新申报 VAT。

    参数:
        invoice_id: int  原发票 ID
        reason: str  冲红原因 (会记入审计日志)
    """
    from commands.orders import ReverseInvoice

    invoice_id = arguments.get("invoice_id")
    if not invoice_id:
        raise BusinessError(code=None, message="invoice_id 必填")

    result = tool_dispatcher.execute_command(
        ReverseInvoice,
        invoice_id=invoice_id,
        reason=arguments.get("reason", "MCP agent 发起冲红"),
    )
    return {
        "ok": True,
        "operation": "reverse_invoice",
        "invoice_id": invoice_id,
        "result": _safe_serialize(result),
        "accounting_hint": (
            "红字发票冲红: 原发票 is_reversed=True, 生成红字发票 (金额取负)。"
            "级联冲红关联 expense 凭证。已申报 VAT 的需重新申报。"
        ),
    }


def reverse_expense(arguments: dict) -> dict:
    """费用冲红 (写操作, 危险)。

    调用路径: dispatch(ReverseExpense(expense_id))
    会红冲 expense 凭证, 标记 expense.is_reversed=True。
    铁律: 已过账 Expense 禁止直接删除, 必须通过本 tool 冲红。

    参数:
        expense_id: int  原费用 ID
        reason: str  冲红原因 (记入 notes, Command 本身无 reason 字段)
    """
    from commands.cash_commands import ReverseExpense

    expense_id = arguments.get("expense_id")
    if not expense_id:
        raise BusinessError(code=None, message="expense_id 必填")

    result = tool_dispatcher.execute_command(
        ReverseExpense,
        expense_id=expense_id,
    )
    return {
        "ok": True,
        "operation": "reverse_expense",
        "expense_id": expense_id,
        "reason": arguments.get("reason", ""),
        "result": _safe_serialize(result),
        "accounting_hint": (
            "费用冲红: expense.is_reversed=True, 生成反向凭证冲红原 6601/2202 分录。"
        ),
    }


def reverse_receipt(arguments: dict) -> dict:
    """收款冲红 (写操作, 危险)。

    调用路径: dispatch(ReverseReceipt(receipt_id))
    生成一笔负数 Receipt + 反向银行流水 + 红冲 receipt 凭证 + 销售单 payment_status 重置。

    参数:
        receipt_id: int  原收款 ID
        reason: str  冲红原因
    """
    from commands.cash_commands import ReverseReceipt

    receipt_id = arguments.get("receipt_id")
    if not receipt_id:
        raise BusinessError(code=None, message="receipt_id 必填")

    result = tool_dispatcher.execute_command(
        ReverseReceipt,
        receipt_id=receipt_id,
    )
    return {
        "ok": True,
        "operation": "reverse_receipt",
        "receipt_id": receipt_id,
        "reason": arguments.get("reason", ""),
        "result": _safe_serialize(result),
        "accounting_hint": (
            "收款冲红: 生成负数 Receipt + 反向银行流水 + 红冲 1002/1122 凭证, "
            "关联销售单 payment_status 重置为 unpaid。"
        ),
    }


def reverse_payment(arguments: dict) -> dict:
    """付款冲红 (写操作, 危险)。

    调用路径: dispatch(ReversePayment(payment_id))
    生成一笔负数 Payment + 反向银行流水 + 红冲 payment 凭证 + 采购单 payment_status 重置。

    参数:
        payment_id: int  原付款 ID
        reason: str  冲红原因
    """
    from commands.cash_commands import ReversePayment

    payment_id = arguments.get("payment_id")
    if not payment_id:
        raise BusinessError(code=None, message="payment_id 必填")

    result = tool_dispatcher.execute_command(
        ReversePayment,
        payment_id=payment_id,
    )
    return {
        "ok": True,
        "operation": "reverse_payment",
        "payment_id": payment_id,
        "reason": arguments.get("reason", ""),
        "result": _safe_serialize(result),
        "accounting_hint": (
            "付款冲红: 生成负数 Payment + 反向银行流水 + 红冲凭证, "
            "关联采购单 payment_status 重置。"
        ),
    }


# ══════════════════════════════════════════════════════════════
# 27-30. 主数据细粒度创建 (P3, 替代粗粒度 setup_basic_data)
# ══════════════════════════════════════════════════════════════
def _add_single_entity(model_cls, arguments: dict, field_name: str, build_dict_fn) -> dict:
    """通用单条主数据创建 (开写权限, operator='ai')。"""
    from database import SessionLocal, _request_write_perm
    account_id = account_context.require_account_id()
    db = SessionLocal()
    db.expire_on_commit = False
    token = _request_write_perm.set(True)
    try:
        obj = model_cls(account_id=account_id, **build_dict_fn(arguments))
        db.add(obj)
        db.flush()
        from lineage import writes, TIER_L3
        db.commit()
        return {"ok": True, field_name: _safe_serialize(obj)}
    except Exception:
        db.rollback()
        raise
    finally:
        _request_write_perm.reset(token)
        db.close()


def add_product(arguments: dict) -> dict:
    """新增单个商品 (写操作)。

    参数:
        name: str  商品名称
        sku: str  SKU (可选, 默认按名称生成)
        category: str  类别 (默认 "商品")
        unit: str  单位 (默认 "个")
        track_inventory: bool  是否跟踪库存 (True→1405 库存, False→6601 费用, 默认 True)
    """
    import models
    name = arguments.get("name")
    if not name:
        raise BusinessError(code=None, message="name 必填")

    def _build(args):
        return {
            "name": name,
            "sku": args.get("sku", f"SKU-{name[:8]}"),
            "category": args.get("category", "商品"),
            "unit": args.get("unit", "个"),
            "track_inventory_l3": args.get("track_inventory", True),
        }
    return _add_single_entity(models.Product, arguments, "product", _build)


def add_customer(arguments: dict) -> dict:
    """新增单个客户 (写操作)。

    参数:
        name: str  客户名称
    """
    import models
    name = arguments.get("name")
    if not name:
        raise BusinessError(code=None, message="name 必填")
    return _add_single_entity(models.Customer, arguments, "customer", lambda a: {"name": name})


def add_supplier(arguments: dict) -> dict:
    """新增单个供应商 (写操作)。

    参数:
        name: str  供应商名称
    """
    import models
    name = arguments.get("name")
    if not name:
        raise BusinessError(code=None, message="name 必填")
    return _add_single_entity(models.Supplier, arguments, "supplier", lambda a: {"name": name})


def add_bank_account(arguments: dict) -> dict:
    """新增单个银行账户 (写操作)。

    参数:
        bank_name: str  银行名称
        account_number: str  账号
    """
    import models
    bank_name = arguments.get("bank_name")
    if not bank_name:
        raise BusinessError(code=None, message="bank_name 必填")
    return _add_single_entity(
        models.BankAccount, arguments, "bank_account",
        lambda a: {"bank_name": bank_name, "account_number": a.get("account_number", "")}
    )


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
            "附加税是 L1 用户输入: 三个金额必须由用户从税务局申报表抄录, 不是系统派生。"
            "月结时 engine_tax.calculate_surcharges 会自动计提附加税凭证 (L3 派生)。"
            "附加税随增值税申报周期: 小规模按季, 一般纳税人按月。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "小规模 YYYY-QQ / 一般纳税人 YYYY-MM"},
                "urban_construction_tax": {"type": "number", "description": "城建税金额 (用户从税务局申报表抄录)"},
                "education_surcharge": {"type": "number", "description": "教育费附加金额"},
                "local_education_surcharge": {"type": "number", "description": "地方教育附加金额"},
                "notes": {"type": "string"},
            },
            "required": ["period", "urban_construction_tax", "education_surcharge", "local_education_surcharge"],
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
            "查询资产负债表 (会小企01表), 默认带 trace 追溯链和对账结果。"
            "字段的 contributions 会列出构成来源 (凭证/发票/库存流水)。"
            "只读, 不修改数据。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "reconcile": {"type": "boolean", "default": True, "description": "是否返回对账结果"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_income_statement",
        "description": (
            "查询利润表 (会小企02表), 默认带 trace 追溯链和对账结果。"
            "只读, 不修改数据。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "reconcile": {"type": "boolean", "default": True, "description": "是否返回对账结果"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    # ── 11. 历史查询 (P0 补全: agent 解释报表/回答用户疑问) ──
    {
        "name": "list_invoices",
        "description": (
            "查询发票列表 (只读)。支持按 direction / 日期范围 / 购销方名称过滤。"
            "agent 解释'上个月开了多少票'、'那笔联通的发票在哪天'时用。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["out", "in"], "description": "out 销项 / in 进项"},
                "date_from": {"type": "string", "description": "YYYY-MM-DD (含)"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD (含)"},
                "counterparty_name": {"type": "string", "description": "购销方名称模糊匹配"},
                "limit": {"type": "integer", "default": 100, "maximum": 500},
            },
        },
    },
    {
        "name": "get_sale_order",
        "description": (
            "查询销售单详情 (含 items + 关联发票 + 收款记录, 只读)。"
            "agent 回答'那笔 1500 元的销售单怎么回事'时用。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_purchase_order",
        "description": (
            "查询采购单详情 (含 items + 关联发票, 只读)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "list_journal_entries",
        "description": (
            "查询会计凭证分录 (只读)。agent 解释报表项目时, 用此 tool 拿到底层凭证。"
            "支持按日期范围 / move_type / source_model 过滤。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD"},
                "move_type": {"type": "string", "description": "sale_order/purchase_order/receipt/payment/expense/..."},
                "source_model": {"type": "string", "description": "sale_order/purchase_order/expense/fixed_asset/..."},
                "limit": {"type": "integer", "default": 100, "maximum": 500},
            },
        },
    },
    # ── 12. 红冲 (P0 补全: 引导用户修正错误) ──
    {
        "name": "reverse_invoice",
        "description": (
            "红字发票冲红 (写操作, 危险)。"
            "会级联冲红关联的 expense 凭证, 标记原发票 is_reversed=True。"
            "铁律: 已申报 VAT 的发票冲红后, 必须重新申报 VAT。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer"},
                "reason": {"type": "string", "description": "冲红原因 (记入审计日志)"},
            },
            "required": ["invoice_id"],
        },
    },
    {
        "name": "reverse_expense",
        "description": (
            "费用冲红 (写操作, 危险)。"
            "铁律: 已过账 Expense 禁止直接删除, 必须通过本 tool 冲红。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "expense_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["expense_id"],
        },
    },
    {
        "name": "reverse_receipt",
        "description": (
            "收款冲红 (写操作, 危险)。"
            "生成负数 Receipt + 反向银行流水 + 红冲凭证 + 销售单 payment_status 重置。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "receipt_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["receipt_id"],
        },
    },
    {
        "name": "reverse_payment",
        "description": (
            "付款冲红 (写操作, 危险)。"
            "生成负数 Payment + 反向银行流水 + 红冲凭证 + 采购单 payment_status 重置。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["payment_id"],
        },
    },
    # ── 13. 主数据细粒度创建 (P3, 替代粗粒度 setup_basic_data) ──
    {
        "name": "add_product",
        "description": "新增单个商品 (写操作)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "sku": {"type": "string"},
                "category": {"type": "string", "default": "商品"},
                "unit": {"type": "string", "default": "个"},
                "track_inventory": {"type": "boolean", "default": True, "description": "True→1405 库存, False→6601 费用"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "add_customer",
        "description": "新增单个客户 (写操作)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "add_supplier",
        "description": "新增单个供应商 (写操作)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "add_bank_account",
        "description": "新增单个银行账户 (写操作)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bank_name": {"type": "string"},
                "account_number": {"type": "string"},
            },
            "required": ["bank_name"],
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
    # P0 补全: 历史查询
    "list_invoices": list_invoices,
    "get_sale_order": get_sale_order,
    "get_purchase_order": get_purchase_order,
    "list_journal_entries": list_journal_entries,
    # P0 补全: 红冲
    "reverse_invoice": reverse_invoice,
    "reverse_expense": reverse_expense,
    "reverse_receipt": reverse_receipt,
    "reverse_payment": reverse_payment,
    # P3 补全: 主数据细粒度
    "add_product": add_product,
    "add_customer": add_customer,
    "add_supplier": add_supplier,
    "add_bank_account": add_bank_account,
}
