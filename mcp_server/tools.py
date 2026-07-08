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
# 辅助: dry_run / 跨期警告 / 已月结校验 (批次 1 共享)
# ──────────────────────────────────────────────────────────────
def _check_business_date(biz_date, tool_name: str) -> tuple[bool, list]:
    """检查业务日期是否跨期或所在月份已月结。

    返回: (is_period_closed, warnings)
        is_period_closed: True 表示该月份已月结, 写操作应被拒绝
        warnings: 跨期警告列表 (该月份未月结但早于当前月份)
    """
    if not biz_date:
        return False, []
    if isinstance(biz_date, str):
        biz_date = _parse_date(biz_date)
    if not biz_date:
        return False, []

    today = date.today()
    warnings = []

    # 跨期: 业务日期早于当前月份的 1 号
    if biz_date < today.replace(day=1):
        warnings.append(
            f"业务日期 {biz_date.isoformat()} 属于已过去月份, "
            f"如该月已月结, 补录会让报表和申报数据不一致。建议走调整凭证。"
        )

    # 查该月份是否已月结 (PeriodClose 是否已执行)
    is_closed = False
    def _check_closed(db, aid):
        from models_finance import AccountMove
        from sqlalchemy import extract
        # 月份已月结的标志: 该月有 source_model='period_close' 的已过账凭证
        cnt = db.query(AccountMove).filter(
            AccountMove.source_model == "period_close",
            AccountMove.state == "posted",
            extract("year", AccountMove.date_l1) == biz_date.year,
            extract("month", AccountMove.date_l1) == biz_date.month,
        ).count()
        return cnt > 0

    try:
        is_closed = tool_dispatcher.run_readonly(_check_closed)
    except Exception:
        # 查询失败不阻塞, 只记 warning
        warnings.append("无法确认该月份是否已月结, 请用户手动核实。")

    if is_closed:
        warnings.append(
            f"{biz_date.strftime('%Y-%m')} 已月结 (损益已结转), "
            f"补录会让该月报表失真。如确需补录, 请走调整凭证或反月结流程。"
        )

    return is_closed, warnings


def _make_dry_run_result(operation: str, amount_with_tax=None, tax_amount=None,
                         amount_without_tax=None, extra: dict = None,
                         accounting_hint: str = "") -> dict:
    """构造 dry_run 预演结果 (不写库)。"""
    out = {
        "ok": True,
        "dry_run": True,
        "operation": operation,
        "message": "dry_run=True, 未实际写库。确认无误后重调本 tool 并传 dry_run=False。",
        "accounting_hint": accounting_hint,
    }
    if amount_with_tax is not None:
        out["amount_with_tax"] = float(amount_with_tax)
    if tax_amount is not None:
        out["tax_amount"] = float(tax_amount)
    if amount_without_tax is not None:
        out["amount_without_tax"] = float(amount_without_tax)
    if extra:
        out.update(extra)
    return out


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
    """列出当前账本所有商品, 支持名称模糊搜索。"""
    name_like = arguments.get("name_like")
    def _query(db, aid):
        import models
        q = db.query(models.Product).filter(models.Product.account_id == aid)
        if name_like:
            q = q.filter(models.Product.name.ilike(f"%{name_like}%"))
        items = q.order_by(models.Product.id.asc()).all()
        return [{
            "id": p.id, "name": p.name, "sku": p.sku,
            "category": p.category, "unit": p.unit,
            "track_inventory": p.track_inventory_l3,
            "purchase_price": float(p.purchase_price_l3) if p.purchase_price_l3 else 0,
        } for p in items]
    return {"ok": True, "products": tool_dispatcher.run_readonly(_query)}


def list_customers(arguments: dict) -> dict:
    """列出当前账本所有客户, 支持名称模糊搜索。"""
    name_like = arguments.get("name_like")
    def _query(db, aid):
        import models
        q = db.query(models.Customer).filter(models.Customer.account_id == aid)
        if name_like:
            q = q.filter(models.Customer.name.ilike(f"%{name_like}%"))
        items = q.order_by(models.Customer.id.asc()).all()
        return [{"id": c.id, "name": c.name} for c in items]
    return {"ok": True, "customers": tool_dispatcher.run_readonly(_query)}


def list_suppliers(arguments: dict) -> dict:
    """列出当前账本所有供应商, 支持名称模糊搜索。"""
    name_like = arguments.get("name_like")
    def _query(db, aid):
        import models
        q = db.query(models.Supplier).filter(models.Supplier.account_id == aid)
        if name_like:
            q = q.filter(models.Supplier.name.ilike(f"%{name_like}%"))
        items = q.order_by(models.Supplier.id.asc()).all()
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
    dry_run = bool(arguments.get("dry_run", False))

    # 价税分离 (与 sim 一致)
    amount_with_tax = sum(
        Decimal(str(it["quantity"])) * Decimal(str(it["unit_price"]))
        for it in items
    ).quantize(Q2, rounding=ROUND_HALF_UP)
    tax_rate = Decimal(str(items[0]["tax_rate"]))
    amount_without_tax, tax_amount = _split_amounts(amount_with_tax, tax_rate)

    # 跨期 / 已月结校验
    is_closed, date_warnings = _check_business_date(sale_date, "create_sale_order_with_invoice")
    if is_closed and not dry_run:
        raise BusinessError(
            code=None,
            message=f"业务日期 {sale_date.isoformat()} 所在月份已月结, 禁止直接补录。请走调整凭证或反月结流程。",
            data={"warnings": date_warnings, "user_message": "这个月份已经月结了, 不能直接补录, 需要走调整凭证。"},
        )

    # dry_run: 只返回金额预演, 不写库
    if dry_run:
        return _make_dry_run_result(
            operation="create_sale_order_with_invoice",
            amount_with_tax=amount_with_tax,
            amount_without_tax=amount_without_tax,
            tax_amount=tax_amount,
            extra={
                "customer_name": customer_name,
                "sale_date": sale_date.isoformat(),
                "items_count": len(items),
                "tax_rate": float(tax_rate),
                "invoice_type": arguments.get("invoice_type", "ordinary"),
                "warnings": date_warnings,
            },
            accounting_hint=(
                "会计影响: 借:应收账款 贷:主营业务收入+应交税费-销项税额。"
                "实物商品 (track_inventory=True) 还会: 借:主营业务成本 贷:库存商品 (按 unit_cost 加权平均)。"
                "服务类商品 (track_inventory=False) 不结转成本。"
            ),
        )

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
        "amount_without_tax": float(amount_without_tax),
        "tax_amount": float(tax_amount),
        "warnings": date_warnings,
        "accounting_hint": (
            "发票驱动: 先开发票自动生成销售单。"
            "会计影响: 借:应收账款 贷:主营业务收入+应交税费-销项税额。"
            "实物商品还会: 借:主营业务成本 贷:库存商品 (按 unit_cost 加权平均); "
            "服务类商品不结转成本。"
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
    dry_run = bool(arguments.get("dry_run", False))

    amount_with_tax = sum(
        Decimal(str(it["quantity"])) * Decimal(str(it["unit_price"]))
        for it in items
    ).quantize(Q2, rounding=ROUND_HALF_UP)
    tax_rate = Decimal(str(items[0]["tax_rate"]))
    amount_without_tax, tax_amount = _split_amounts(amount_with_tax, tax_rate)

    # 跨期 / 已月结校验
    is_closed, date_warnings = _check_business_date(purchase_date, "create_purchase_order_with_invoice")
    if is_closed and not dry_run:
        raise BusinessError(
            code=None,
            message=f"业务日期 {purchase_date.isoformat()} 所在月份已月结, 禁止直接补录。",
            data={"warnings": date_warnings, "user_message": "这个月份已经月结了, 不能直接补录, 需要走调整凭证。"},
        )

    if dry_run:
        return _make_dry_run_result(
            operation="create_purchase_order_with_invoice",
            amount_with_tax=amount_with_tax,
            amount_without_tax=amount_without_tax,
            tax_amount=tax_amount,
            extra={
                "supplier_name": supplier_name,
                "purchase_date": purchase_date.isoformat(),
                "items_count": len(items),
                "tax_rate": float(tax_rate),
                "warnings": date_warnings,
            },
            accounting_hint=(
                "会计影响: 借:库存商品 借:应交税费-进项税额 贷:应付账款。"
                "小规模纳税人进项税不可抵扣, 含税全额入库存成本。"
            ),
        )

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
        "amount_without_tax": float(amount_without_tax),
        "tax_amount": float(tax_amount),
        "warnings": date_warnings,
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
    dry_run = bool(arguments.get("dry_run", False))
    amt = Decimal(str(amount))

    # 跨期 / 已月结校验
    is_closed, date_warnings = _check_business_date(payment_date_str, "create_receipt")
    if is_closed and not dry_run:
        raise BusinessError(
            code=None,
            message=f"收款日期 {payment_date_str} 所在月份已月结, 禁止直接补录。",
            data={"warnings": date_warnings, "user_message": "这个月份已经月结了, 不能直接补录。"},
        )

    if dry_run:
        return _make_dry_run_result(
            operation="create_receipt",
            amount_with_tax=amt,
            extra={
                "sale_order_id": sale_order_id,
                "payment_date": payment_date_str,
                "bank_account_id": arguments.get("bank_account_id"),
                "warnings": date_warnings,
            },
            accounting_hint="客户收款: 借:1002 银行存款 贷:1122 应收账款。",
        )

    data = ReceiptCreate(
        receipt_type="sale",
        related_entity_type="sale_order",
        related_entity_id=sale_order_id,
        amount=amt,
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
        "amount": float(amt),
        "warnings": date_warnings,
        "accounting_hint": "客户收款: 借:1002 银行存款 贷:1122 应收账款。",
    }


# ══════════════════════════════════════════════════════════════
# 9b. 付款: create_payment (付给供应商/发工资/缴税)
# ══════════════════════════════════════════════════════════════
def create_payment(arguments: dict) -> dict:
    """付款给供应商 / 发工资 / 缴税 (银行流出)。

    对应 commands.cash_commands.CreatePayment。
    会计影响: 借:2202 应付账款(采购/费用) / 2211 应付职工薪酬(工资) / 2221 应交税费(缴税)
              贷:1002 银行存款。
    发工资时 withholding_tax_amount 为代扣个税, 实发=amount, 应发=amount+withholding_tax_amount。

    参数:
        payment_type: str  付款类型 (expense/purchase/salary/tax)
        related_entity_type: str  关联实体类型 (expense/purchase_order/tax_payable)
        related_entity_id: int  关联实体 ID
        amount: float  付款金额 (实发, >0)
        payment_date: str  付款日期 (YYYY-MM-DD)
        bank_account_id: int  银行账户 ID (可选, 默认取首个)
        withholding_tax_amount: float  代扣个税 (仅 salary, 默认 0)
        description: str  描述
        dry_run: bool  仅预演, 不写库
    """
    from commands.cash_commands import CreatePayment
    from schemas.payment import PaymentCreate

    payment_type = arguments.get("payment_type")
    related_entity_type = arguments.get("related_entity_type")
    related_entity_id = arguments.get("related_entity_id")
    amount = arguments.get("amount")
    payment_date_str = arguments.get("payment_date")

    if not payment_type or payment_type not in ("expense", "purchase", "salary", "tax"):
        raise BusinessError(code=None, message="payment_type 必填且必须是 expense/purchase/salary/tax")
    if not related_entity_type:
        raise BusinessError(code=None, message="related_entity_type 必填 (expense/purchase_order/tax_payable)")
    if not related_entity_id:
        raise BusinessError(code=None, message="related_entity_id 必填")
    if amount is None or amount <= 0:
        raise BusinessError(code=None, message="amount 必填且必须 > 0")
    if not payment_date_str:
        raise BusinessError(code=None, message="payment_date 必填 (YYYY-MM-DD)")

    payment_date = _to_datetime(payment_date_str)
    dry_run = bool(arguments.get("dry_run", False))
    amt = Decimal(str(amount))
    withholding = Decimal(str(arguments.get("withholding_tax_amount", 0) or 0))

    # salary 才能用 withholding_tax_amount
    if withholding > 0 and payment_type != "salary":
        raise BusinessError(
            code=None,
            message=f"withholding_tax_amount 仅 payment_type=salary 可用, 当前 payment_type={payment_type}",
        )

    # 跨期 / 已月结校验
    is_closed, date_warnings = _check_business_date(payment_date_str, "create_payment")
    if is_closed and not dry_run:
        raise BusinessError(
            code=None,
            message=f"付款日期 {payment_date_str} 所在月份已月结, 禁止直接补录。",
            data={"warnings": date_warnings, "user_message": "这个月份已经月结了, 不能直接补录。"},
        )

    # 会计科目映射 (借方)
    debit_code_map = {"expense": "2202", "purchase": "2202", "salary": "2211", "tax": "2221"}
    debit_code = debit_code_map.get(payment_type, "2202")
    hint = f"付款: 借:{debit_code} 贷:1002 银行存款。"
    if payment_type == "salary" and withholding > 0:
        hint += f" 代扣个税 {float(withholding)} (应发={float(amt)+float(withholding)}, 实发={float(amt)})。"

    if dry_run:
        return _make_dry_run_result(
            operation="create_payment",
            amount_with_tax=amt,
            extra={
                "payment_type": payment_type,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id,
                "payment_date": payment_date_str,
                "bank_account_id": arguments.get("bank_account_id"),
                "withholding_tax_amount": float(withholding),
                "warnings": date_warnings,
            },
            accounting_hint=hint,
        )

    data = PaymentCreate(
        payment_type=payment_type,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        amount=amt,
        withholding_tax_amount=withholding,
        payment_method="company",
        payment_date=payment_date,
        bank_account_id=arguments.get("bank_account_id"),
        description=arguments.get("description", ""),
    )

    result = tool_dispatcher.execute_command(CreatePayment, data=data)
    return {
        "ok": True,
        "operation": "create_payment",
        "result": _safe_serialize(result),
        "amount": float(amt),
        "warnings": date_warnings,
        "accounting_hint": hint,
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
    dry_run = bool(arguments.get("dry_run", False))
    amt = Decimal(str(amount))

    # 跨期 / 已月结校验
    is_closed, date_warnings = _check_business_date(expense_date_str, "create_expense")
    if is_closed and not dry_run:
        raise BusinessError(
            code=None,
            message=f"费用日期 {expense_date_str} 所在月份已月结, 禁止直接补录。",
            data={"warnings": date_warnings, "user_message": "这个月份已经月结了, 不能直接补录。"},
        )

    if dry_run:
        return _make_dry_run_result(
            operation="create_expense",
            amount_with_tax=amt,
            extra={
                "category": category,
                "expense_date": expense_date_str,
                "functional_category": arguments.get("functional_category", "管理费用"),
                "payment_method": arguments.get("payment_method", "company"),
                "warnings": date_warnings,
            },
            accounting_hint=(
                "费用入账: 借:6601 管理费用 (或 6602 销售/6603 财务) "
                "贷:2202 应付账款 (公司采购) / 2241 其他应付款 (个人垫付)。"
            ),
        )

    expense = ExpenseCreate(
        category=category,
        functional_category=arguments.get("functional_category", "管理费用"),
        amount=amt,
        expense_date=expense_date,
        payment_method=arguments.get("payment_method", "company"),
        description=arguments.get("description", ""),
    )

    result = tool_dispatcher.execute_command(CreateExpense, expense=expense)
    return {
        "ok": True,
        "operation": "create_expense",
        "result": _safe_serialize(result),
        "amount": float(amt),
        "warnings": date_warnings,
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

    dry_run = bool(arguments.get("dry_run", False))
    amt = Decimal(str(amount))

    # 跨期 / 已月结校验
    is_closed, date_warnings = _check_business_date(transaction_date_str, "create_bank_entry")
    if is_closed and not dry_run:
        raise BusinessError(
            code=None,
            message=f"交易日期 {transaction_date_str} 所在月份已月结, 禁止直接补录。",
            data={"warnings": date_warnings, "user_message": "这个月份已经月结了, 不能直接补录。"},
        )

    hint = (
        "银行扣款: 借:6603 财务费用 贷:1002 银行存款。"
        if entry_type == "bank_fee"
        else "利息收入: 借:1002 银行存款 贷:6603 财务费用 (冲减财务费用, 不进 6301 营业外收入)。"
    )

    if dry_run:
        return _make_dry_run_result(
            operation="create_bank_entry",
            amount_with_tax=amt,
            extra={
                "entry_type": entry_type,
                "transaction_date": transaction_date_str,
                "warnings": date_warnings,
            },
            accounting_hint=hint,
        )

    result = tool_dispatcher.execute_command(
        CreateBankEntry,
        entry_type=entry_type,
        amount=float(amount),
        transaction_date=transaction_date_str,
        description=arguments.get("description", ""),
        bank_account_id=arguments.get("bank_account_id"),
    )
    return {
        "ok": True,
        "operation": "create_bank_entry",
        "result": _safe_serialize(result),
        "amount": float(amt),
        "warnings": date_warnings,
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
    dry_run = bool(arguments.get("dry_run", False))
    cost_dec = Decimal(str(cost))
    salvage_rate = Decimal(str(arguments.get("salvage_rate", 0.05)))
    useful_life = arguments.get("useful_life", 60)

    # 跨期 / 已月结校验 (固定资产采购日期影响应付账款, 不直接结转损益, 但仍需警告)
    is_closed, date_warnings = _check_business_date(purchase_date_str, "create_fixed_asset")

    monthly_depr = ((cost_dec * (Decimal("1") - salvage_rate)) / Decimal(str(useful_life))).quantize(Q2, rounding=ROUND_HALF_UP)

    if dry_run:
        return _make_dry_run_result(
            operation="create_fixed_asset",
            amount_with_tax=cost_dec,
            extra={
                "name": name,
                "purchase_date": purchase_date_str,
                "asset_code": asset_code,
                "category": arguments.get("category", "电子设备"),
                "salvage_rate": float(salvage_rate),
                "useful_life": useful_life,
                "monthly_depreciation": float(monthly_depr),
                "warnings": date_warnings,
            },
            accounting_hint=(
                "固定资产入账: 借:1601 固定资产 贷:2202 应付账款 / 2241 其他应付款。"
                f"次月起按月计提折旧: 借:6601/6602 贷:1602 累计折旧 (每月 {float(monthly_depr):.2f} 元)。"
            ),
        )

    data = FixedAssetCreate(
        asset_code=asset_code,
        name=name,
        category=arguments.get("category", "电子设备"),
        original_value=cost_dec,
        salvage_rate=salvage_rate,
        useful_life=useful_life,
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
            "amount": float(cost_dec),
            "monthly_depreciation": float(monthly_depr),
            "warnings": date_warnings,
            "accounting_hint": (
                "固定资产入账: 借:1601 固定资产 贷:2202 应付账款 (公司采购) / "
                "2241 其他应付款 (个人垫付 private_advance)。"
                f"次月起按月计提折旧: 借:6601/6602 管理费用/销售费用 贷:1602 累计折旧 (每月 {float(monthly_depr):.2f} 元)。"
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
        dry_run: bool  仅预演 (返回哪些资产会折旧+每月折旧金额), 不写库
    """
    from commands.fixed_asset_commands import BatchDepreciateFixedAssets

    period = arguments.get("period")
    if not period:
        raise BusinessError(code=None, message="period 必填 (YYYY-MM)")
    # 校验 period 格式 (YYYY-MM)
    _validate_period_by_taxpayer(period, tool_name="month_end_close")
    dry_run = bool(arguments.get("dry_run", False))

    # 检查目标月份是否已月结 (复用 month_end_close 的逻辑)
    def _check_closed(db, aid):
        from models_finance import AccountMove
        from sqlalchemy import extract
        year_part, month_part = period.split("-")
        cnt = db.query(AccountMove).filter(
            AccountMove.source_model == "period_close",
            AccountMove.state == "posted",
            extract("year", AccountMove.date_l1) == int(year_part),
            extract("month", AccountMove.date_l1) == int(month_part),
        ).count()
        return cnt > 0

    already_closed = False
    try:
        already_closed = tool_dispatcher.run_readonly(_check_closed)
    except Exception:
        pass

    if already_closed and not dry_run:
        raise BusinessError(
            code=None,
            message=f"{period} 已月结, 重复折旧会让报表错乱。",
            data={"user_message": f"{period} 已经月结过了, 不能重复折旧。"},
        )

    # dry_run: 预览哪些资产会折旧 + 每月折旧金额
    if dry_run:
        def _preview(db, aid):
            import models
            from decimal import Decimal, ROUND_HALF_UP
            assets = db.query(models.FixedAsset).filter(
                models.FixedAsset.account_id == aid,
                models.FixedAsset.status == "在用",
            ).all()
            preview = []
            total = Decimal("0")
            for a in assets:
                monthly = (Decimal(str(a.original_value_l1)) * (Decimal("1") - Decimal(str(a.salvage_rate_l3)))
                           / Decimal(str(a.useful_life_l3))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                preview.append({
                    "id": a.id, "name": a.name,
                    "original_value": float(a.original_value_l1),
                    "monthly_depreciation": float(monthly),
                })
                total += monthly
            return {"assets": preview, "total": float(total), "count": len(preview)}

        preview_data = tool_dispatcher.run_readonly(_preview)
        return _make_dry_run_result(
            operation="batch_depreciate",
            extra={
                "period": period,
                "already_closed": already_closed,
                "preview": preview_data,
                "warnings": ([f"{period} 已月结, 实际折旧会被拒绝。"] if already_closed else []),
            },
            accounting_hint=f"月度折旧计提: {preview_data['count']} 个资产, 合计 {preview_data['total']:.2f}。",
        )

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
    dry_run = bool(arguments.get("dry_run", False))

    # 重复申报校验: 同一 period 不能重复申报 VAT
    def _check_existing_vat(db, aid):
        from models_finance import VATDeclaration
        existing = db.query(VATDeclaration).filter(
            VATDeclaration.account_id == aid,
            VATDeclaration.period == period,
        ).first()
        if existing:
            return {
                "id": existing.id,
                "total_revenue": float(existing.total_revenue or 0),
                "vat_payable": float(existing.vat_payable or 0),
            }
        return None

    existing_vat = tool_dispatcher.run_readonly(_check_existing_vat)
    if existing_vat and not dry_run:
        raise BusinessError(
            code=None,
            message=f"period={period} 已存在 VAT 申报记录 (id={existing_vat['id']}, "
                    f"应纳增值税={existing_vat['vat_payable']:.2f})。禁止重复申报。"
                    f"如需重新申报, 请先 reverse 旧申报。",
            data={
                "existing_declaration": existing_vat,
                "user_message": f"{period} 已经申报过增值税了, 不能重复申报。要先撤销旧申报才能重新申报。",
            },
        )

    if dry_run:
        return _make_dry_run_result(
            operation="declare_vat",
            extra={
                "period": period,
                "taxpayer_type": taxpayer_type,
                "existing_declaration": existing_vat,
                "warnings": ([f"{period} 已存在 VAT 申报 (id={existing_vat['id']}), 实际申报会被拒绝。"]
                             if existing_vat else []),
            },
            accounting_hint="VAT 申报会生成应交税费凭证, 不可重复申报。",
        )

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
    dry_run = bool(arguments.get("dry_run", False))

    # 重复申报校验: 同一 period 不能重复申报附加税
    def _check_existing_surcharge(db, aid):
        from models_finance import SurchargeDeclaration
        existing = db.query(SurchargeDeclaration).filter(
            SurchargeDeclaration.account_id == aid,
            SurchargeDeclaration.period == period,
        ).first()
        if existing:
            return {
                "id": existing.id,
                "urban": float(existing.urban_construction_tax or 0),
                "edu": float(existing.education_surcharge or 0),
                "local_edu": float(existing.local_education_surcharge or 0),
            }
        return None

    existing_sg = tool_dispatcher.run_readonly(_check_existing_surcharge)
    if existing_sg and not dry_run:
        raise BusinessError(
            code=None,
            message=f"period={period} 已存在附加税申报记录 (id={existing_sg['id']})。禁止重复申报。"
                    f"如需重新申报, 请先 reverse 旧申报。",
            data={
                "existing_declaration": existing_sg,
                "user_message": f"{period} 已经申报过附加税了, 不能重复申报。要先撤销旧申报才能重新申报。",
            },
        )

    # 算 suggested_amounts 供用户参考 (不强制使用, 最终以用户输入为准)
    def _calc_suggested(db, aid):
        from models_finance import VATDeclaration
        from policy.vat_facts import load_vat_facts
        import models
        acc = db.query(models.Account).filter(models.Account.id == aid).first()
        surcharge_halved = bool(acc.surcharge_halved) if acc else False
        # 查当期 VAT 申报的 vat_payable
        vat = db.query(VATDeclaration).filter(
            VATDeclaration.account_id == aid,
            VATDeclaration.period == period,
        ).first()
        if not vat:
            return None
        vat_payable = Decimal(str(vat.vat_payable or 0))
        if vat_payable <= 0:
            return {"urban": 0, "edu": 0, "local_edu": 0, "vat_payable": float(vat_payable),
                    "note": "VAT 应纳为 0 或负数 (留抵), 无附加税可计提。"}
        facts = load_vat_facts(date.today())
        urban_rate = Decimal("0.07") * (Decimal("0.5") if surcharge_halved else Decimal("1"))
        # 教育附加/地方教育附加: 小规模季度销售额 ≤30 万免征; 一般纳税人不享受
        taxpayer_type = acc.taxpayer_type_l3 if acc else "small_scale"
        # 查季度合计销售额判断是否免征
        if "Q" in period:
            q_periods = [period]
        else:
            year_str, m_str = period.split("-")
            month = int(m_str)
            q_num = (month - 1) // 3 + 1
            q_periods = [f"{year_str}-Q{q_num}"] if taxpayer_type == "small_scale" else [period]
        q_vats = db.query(VATDeclaration).filter(
            VATDeclaration.account_id == aid,
            VATDeclaration.period.in_(q_periods),
        ).all()
        quarterly_revenue = sum((Decimal(str(v.total_revenue or 0)) for v in q_vats), Decimal("0"))
        exempt_threshold = Decimal(str(facts.small_scale_quarterly_exemption))
        edu_exempt = (taxpayer_type == "small_scale" and quarterly_revenue <= exempt_threshold)
        edu_rate = Decimal("0") if edu_exempt else Decimal("0.03")
        local_edu_rate = Decimal("0") if edu_exempt else Decimal("0.02")
        return {
            "urban": float((vat_payable * urban_rate).quantize(Q2, rounding=ROUND_HALF_UP)),
            "edu": float((vat_payable * edu_rate).quantize(Q2, rounding=ROUND_HALF_UP)),
            "local_edu": float((vat_payable * local_edu_rate).quantize(Q2, rounding=ROUND_HALF_UP)),
            "vat_payable": float(vat_payable),
            "quarterly_revenue": float(quarterly_revenue),
            "edu_exempt": edu_exempt,
            "surcharge_halved": surcharge_halved,
            "note": "公式参考值, 实际金额以税务局申报表为准。"
        }

    try:
        suggested = tool_dispatcher.run_readonly(_calc_suggested)
    except Exception:
        suggested = None

    # 金额校验 (实际申报时三个金额必须齐全)
    if not dry_run and (urban is None or edu is None or local_edu is None):
        raise BusinessError(
            code=None,
            message="附加税是 L1 用户输入: urban_construction_tax / education_surcharge / "
                    "local_education_surcharge 三个金额必须由用户提供 (从税务局申报表抄录)。"
                    f"参考值 (公式计算, 非强制): {suggested}",
            data={"suggested_amounts": suggested},
        )

    if dry_run:
        return _make_dry_run_result(
            operation="declare_surcharge",
            extra={
                "period": period,
                "user_input": {"urban": urban, "edu": edu, "local_edu": local_edu},
                "suggested_amounts": suggested,
                "existing_declaration": existing_sg,
                "warnings": ([f"{period} 已存在附加税申报 (id={existing_sg['id']}), 实际申报会被拒绝。"]
                             if existing_sg else []),
            },
            accounting_hint=(
                "附加税申报 (L1 用户输入): 借:6403 税金及附加 贷:222101/222102/222110。"
                "建议把 suggested_amounts 给用户参考, 最终金额以用户从税务局申报表抄录的为准。"
            ),
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
        "suggested_amounts": suggested,
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
    dry_run = bool(arguments.get("dry_run", False))
    # require_confirm: 月结是不可逆写操作, 默认要求用户确认 (传 require_confirm=False 可跳过)
    require_confirm = arguments.get("require_confirm", True)

    # 检查目标月份是否已月结
    def _check_closed(db, aid):
        from models_finance import AccountMove
        from sqlalchemy import extract
        year_part, month_part = period.split("-")
        cnt = db.query(AccountMove).filter(
            AccountMove.source_model == "period_close",
            AccountMove.state == "posted",
            extract("year", AccountMove.date_l1) == int(year_part),
            extract("month", AccountMove.date_l1) == int(month_part),
        ).count()
        return cnt > 0

    already_closed = False
    try:
        already_closed = tool_dispatcher.run_readonly(_check_closed)
    except Exception:
        pass

    if already_closed and not dry_run:
        raise BusinessError(
            code=None,
            message=f"{period} 已月结, 重复月结会重复结转损益导致报表错乱。",
            data={"user_message": f"{period} 已经月结过了, 不能重复月结。"},
        )

    if dry_run:
        return _make_dry_run_result(
            operation="month_end_close",
            extra={
                "period": period,
                "already_closed": already_closed,
                "warnings": ([f"{period} 已月结, 实际月结会被拒绝。"] if already_closed
                             else ["月结会执行 5 步, 生成凭证不可逆。执行前请确认用户已授权。"]),
            },
            accounting_hint=(
                "月结 5 步: (1) 折旧/摊销 (2) 增值税+附加税+所得税计提 "
                "(3) 损益结转 4103 (4) 12月年结 4103→4104 (5) 税务核对 8 项。"
            ),
        )

    if require_confirm:
        raise BusinessError(
            code=None,
            message=f"月结 {period} 是不可逆写操作, 会生成凭证并结转损益。"
                    f"请用户明确确认后, 重传 require_confirm=False 执行。",
            data={
                "user_message": f"月结 {period} 不可撤销, 确认要执行吗? 用户确认后请重传 require_confirm=False。",
                "require_confirm": True,
            },
        )

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
        # summary: 挑 6-8 个关键数字给 agent 讲给用户
        values = _extract_values(result)
        summary_keys = [
            "total_assets", "total_liabilities", "total_equity",
            "cash", "inventory", "accounts_receivable", "accounts_payable",
            "retained_earnings", "vat_payable",
        ]
        summary = {k: values.get(k, 0) for k in summary_keys if k in values}
        out = {"ok": True, "date": date_str, "account_id": account_id,
               "summary": summary, "balance_sheet": result}
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
        # summary: 关键数字
        values = _extract_values(result)
        summary_keys = [
            "operating_revenue", "operating_cost", "gross_profit",
            "operating_expenses", "operating_profit", "non_operating_income",
            "non_operating_expenses", "profit_before_tax", "income_tax", "net_profit",
        ]
        summary = {k: values.get(k, 0) for k in summary_keys if k in values}
        out = {"ok": True, "start_date": start_str, "end_date": end_str,
               "account_id": account_id, "summary": summary, "income_statement": result}
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
def _check_reverse_status(entity_type: str, entity_id: int) -> dict:
    """reverse 前检查原单状态, 返回需要警告的信息。

    检查项:
    - 原单是否已红冲 (is_reversed=True)
    - 是否有关联的未红冲单据 (如发票有收款未红冲)
    - 是否已申报 VAT (发票红冲后需重新申报)

    返回: {"already_reversed": bool, "warnings": list, "original": dict}
    """
    def _check(db, aid):
        import models
        from models_finance import VATDeclaration, SurchargeDeclaration, AccountMove
        from sqlalchemy import extract
        warnings = []
        already_reversed = False
        original = {}
        original_date = None  # 原单业务日期, 用于月结检查

        if entity_type == "invoice":
            inv = db.query(models.Invoice).filter(
                models.Invoice.id == entity_id
            ).first()
            if not inv:
                raise BusinessError(code=None, message=f"发票 id={entity_id} 不存在")
            already_reversed = bool(inv.is_reversed)
            original_date = inv.issue_date_l1
            original = {
                "id": inv.id, "direction": inv.direction,
                "amount_with_tax": float(inv.amount_with_tax_l1 or 0),
                "is_reversed": already_reversed,
                "counterparty_name": inv.counterparty_name,
                "date": original_date.isoformat() if original_date else None,
            }
            if already_reversed:
                warnings.append(f"发票 id={entity_id} 已红冲过, 重复红冲无效。")
            # 检查关联收款 (sale_order 的 receipts)
            if inv.direction == "out" and inv.related_order_id:
                receipts = db.query(models.Receipt).filter(
                    models.Receipt.related_entity_type == "sale_order",
                    models.Receipt.related_entity_id == inv.related_order_id,
                    models.Receipt.is_reversed == False,
                ).all()
                if receipts:
                    r_ids = [r.id for r in receipts]
                    warnings.append(
                        f"该销售发票关联 {len(receipts)} 笔未红冲的收款 (id={r_ids})。"
                        f"红冲发票不会自动红冲收款, 应先 reverse_receipt 再 reverse_invoice, "
                        f"否则应收账款和银行存款会对不上。"
                    )
            # 检查是否已申报 VAT
            issue_period = None
            if inv.issue_date_l1:
                m = inv.issue_date_l1.month
                y = inv.issue_date_l1.year
                # 推算申报 period (小规模按季, 一般按月)
                acc = db.query(models.Account).filter(models.Account.id == aid).first()
                if acc and acc.taxpayer_type_l3 == "small_scale":
                    q = (m - 1) // 3 + 1
                    issue_period = f"{y}-Q{q}"
                else:
                    issue_period = f"{y}-{m:02d}"
            if issue_period:
                vat_decl = db.query(VATDeclaration).filter(
                    VATDeclaration.account_id == aid,
                    VATDeclaration.period == issue_period,
                ).first()
                if vat_decl:
                    warnings.append(
                        f"该发票所属期间 {issue_period} 已申报 VAT (declaration_id={vat_decl.id})。"
                        f"红冲后需重新申报 VAT。"
                    )

        elif entity_type == "expense":
            exp = db.query(models.Expense).filter(
                models.Expense.id == entity_id
            ).first()
            if not exp:
                raise BusinessError(code=None, message=f"费用 id={entity_id} 不存在")
            already_reversed = bool(exp.is_reversed)
            original_date = exp.expense_date_l1 if hasattr(exp, "expense_date_l1") else None
            original = {
                "id": exp.id, "category": exp.category,
                "amount": float(exp.amount_l3 or 0) if hasattr(exp, "amount_l3") else float(exp.amount or 0),
                "is_reversed": already_reversed,
                "date": original_date.isoformat() if original_date else None,
            }
            if already_reversed:
                warnings.append(f"费用 id={entity_id} 已红冲过, 重复红冲无效。")

        elif entity_type in ("receipt", "payment"):
            cls = models.Receipt if entity_type == "receipt" else models.Payment
            date_field = "receipt_date_l1" if entity_type == "receipt" else "payment_date_l1"
            obj = db.query(cls).filter(cls.id == entity_id).first()
            if not obj:
                raise BusinessError(code=None, message=f"{entity_type} id={entity_id} 不存在")
            already_reversed = bool(obj.is_reversed)
            original_date = getattr(obj, date_field, None)
            original = {
                "id": obj.id, "amount": float(obj.amount or 0),
                "is_reversed": already_reversed,
                "date": original_date.isoformat() if original_date else None,
            }
            if already_reversed:
                warnings.append(f"{entity_type} id={entity_id} 已红冲过, 重复红冲无效。")

        # 原单月份已月结检查 (warning, 不阻塞)
        if original_date and not already_reversed:
            try:
                cnt = db.query(AccountMove).filter(
                    AccountMove.source_model == "period_close",
                    AccountMove.state == "posted",
                    extract("year", AccountMove.date_l1) == original_date.year,
                    extract("month", AccountMove.date_l1) == original_date.month,
                ).count()
                if cnt > 0:
                    warnings.append(
                        f"原单日期 {original_date.strftime('%Y-%m')} 所在月份已月结, "
                        f"红冲会让该月报表失真。如确需纠正, 建议走调整凭证。"
                    )
            except Exception:
                pass

        return {"already_reversed": already_reversed, "warnings": warnings, "original": original}

    return tool_dispatcher.run_readonly(_check)


def reverse_invoice(arguments: dict) -> dict:
    """红字发票冲红 (写操作, 危险)。

    调用路径: dispatch(ReverseInvoice(invoice_id, reason))
    会级联冲红关联的 expense 凭证, 标记原发票 is_reversed=True。
    铁律: 已申报 VAT 的发票冲红后, 必须重新申报 VAT。

    参数:
        invoice_id: int  原发票 ID
        reason: str  冲红原因 (会记入审计日志)
        dry_run: bool  仅检查原单状态, 不实际红冲
    """
    from commands.orders import ReverseInvoice

    invoice_id = arguments.get("invoice_id")
    if not invoice_id:
        raise BusinessError(code=None, message="invoice_id 必填")
    dry_run = bool(arguments.get("dry_run", False))

    # 原单状态校验
    status = _check_reverse_status("invoice", invoice_id)
    if status["already_reversed"] and not dry_run:
        raise BusinessError(
            code=None,
            message=f"发票 id={invoice_id} 已红冲过, 重复红冲无效。",
            data={"original": status["original"], "user_message": "这张发票已经红冲过了, 不能重复红冲。"},
        )

    if dry_run:
        return _make_dry_run_result(
            operation="reverse_invoice",
            extra={
                "invoice_id": invoice_id,
                "original": status["original"],
                "warnings": status["warnings"],
            },
            accounting_hint="红字发票冲红 (dry_run 未执行): 原发票 is_reversed=True, 生成红字发票。",
        )

    # 有未红冲收款的警告 (不阻塞, 让 agent 决定)
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
        "warnings": status["warnings"],
        "accounting_hint": (
            "红字发票冲红: 原发票 is_reversed=True, 生成红字发票 (金额取负)。"
            "级联冲红关联 expense 凭证。已申报 VAT 的需重新申报。"
            "注意: 不会自动红冲关联收款, 需手动调 reverse_receipt。"
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
        dry_run: bool  仅检查原单状态, 不实际红冲
    """
    from commands.cash_commands import ReverseExpense

    expense_id = arguments.get("expense_id")
    if not expense_id:
        raise BusinessError(code=None, message="expense_id 必填")
    dry_run = bool(arguments.get("dry_run", False))

    status = _check_reverse_status("expense", expense_id)
    if status["already_reversed"] and not dry_run:
        raise BusinessError(
            code=None,
            message=f"费用 id={expense_id} 已红冲过, 重复红冲无效。",
            data={"original": status["original"], "user_message": "这笔费用已经红冲过了, 不能重复红冲。"},
        )

    if dry_run:
        return _make_dry_run_result(
            operation="reverse_expense",
            extra={"expense_id": expense_id, "original": status["original"], "warnings": status["warnings"]},
            accounting_hint="费用冲红 (dry_run 未执行)。",
        )

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
        "warnings": status["warnings"],
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
        dry_run: bool  仅检查原单状态, 不实际红冲
    """
    from commands.cash_commands import ReverseReceipt

    receipt_id = arguments.get("receipt_id")
    if not receipt_id:
        raise BusinessError(code=None, message="receipt_id 必填")
    dry_run = bool(arguments.get("dry_run", False))

    status = _check_reverse_status("receipt", receipt_id)
    if status["already_reversed"] and not dry_run:
        raise BusinessError(
            code=None,
            message=f"收款 id={receipt_id} 已红冲过, 重复红冲无效。",
            data={"original": status["original"], "user_message": "这笔收款已经红冲过了, 不能重复红冲。"},
        )

    if dry_run:
        return _make_dry_run_result(
            operation="reverse_receipt",
            extra={"receipt_id": receipt_id, "original": status["original"], "warnings": status["warnings"]},
            accounting_hint="收款冲红 (dry_run 未执行)。",
        )

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
        "warnings": status["warnings"],
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
        dry_run: bool  仅检查原单状态, 不实际红冲
    """
    from commands.cash_commands import ReversePayment

    payment_id = arguments.get("payment_id")
    if not payment_id:
        raise BusinessError(code=None, message="payment_id 必填")
    dry_run = bool(arguments.get("dry_run", False))

    status = _check_reverse_status("payment", payment_id)
    if status["already_reversed"] and not dry_run:
        raise BusinessError(
            code=None,
            message=f"付款 id={payment_id} 已红冲过, 重复红冲无效。",
            data={"original": status["original"], "user_message": "这笔付款已经红冲过了, 不能重复红冲。"},
        )

    if dry_run:
        return _make_dry_run_result(
            operation="reverse_payment",
            extra={"payment_id": payment_id, "original": status["original"], "warnings": status["warnings"]},
            accounting_hint="付款冲红 (dry_run 未执行)。",
        )

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
        "warnings": status["warnings"],
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
# 31-32. 操作历史与撤销 (P3: 多轮对话上下文恢复)
# ══════════════════════════════════════════════════════════════
def list_recent_operations(arguments: dict) -> dict:
    """列出最近 N 条写操作 (按时间倒序), 帮 agent 定位「刚才那笔」。

    用户说「刚才那笔销售」「昨天那笔费用」「撤销上一步」时用。
    返回每条操作的 id / 类型 / 金额 / 时间 / 是否可撤销。
    """
    limit = min(int(arguments.get("limit", 10)), 50)
    operation_type = arguments.get("operation_type")  # 可选过滤: invoice/receipt/expense/payment

    def _query(db, aid):
        from models_finance import AccountMove
        import models
        results = []

        # 发票 (销项+进项)
        if not operation_type or operation_type == "invoice":
            invs = db.query(models.Invoice).filter(
                models.Invoice.account_id == aid,
                models.Invoice.is_reversed == False,
            ).order_by(models.Invoice.id.desc()).limit(limit).all()
            for inv in invs:
                results.append({
                    "type": "invoice",
                    "id": inv.id,
                    "direction": inv.direction,
                    "amount_with_tax": float(inv.amount_with_tax_l1 or 0),
                    "date": inv.issue_date_l1.isoformat() if inv.issue_date_l1 else None,
                    "counterparty": inv.counterparty_name,
                    "can_undo": True,
                    "undo_tool": "reverse_invoice",
                    "undo_param": "invoice_id",
                })

        # 收款
        if not operation_type or operation_type == "receipt":
            receipts = db.query(models.Receipt).filter(
                models.Receipt.account_id == aid,
                models.Receipt.is_reversed == False,
            ).order_by(models.Receipt.id.desc()).limit(limit).all()
            for r in receipts:
                results.append({
                    "type": "receipt",
                    "id": r.id,
                    "amount": float(r.amount or 0),
                    "date": r.receipt_date_l1.isoformat() if r.receipt_date_l1 else None,
                    "can_undo": True,
                    "undo_tool": "reverse_receipt",
                    "undo_param": "receipt_id",
                })

        # 付款
        if not operation_type or operation_type == "payment":
            payments = db.query(models.Payment).filter(
                models.Payment.account_id == aid,
                models.Payment.is_reversed == False,
            ).order_by(models.Payment.id.desc()).limit(limit).all()
            for p in payments:
                results.append({
                    "type": "payment",
                    "id": p.id,
                    "amount": float(p.amount_l1 or 0) if hasattr(p, "amount_l1") else float(p.amount or 0),
                    "payment_type": getattr(p, "payment_type", None),
                    "date": p.payment_date_l1.isoformat() if p.payment_date_l1 else None,
                    "can_undo": True,
                    "undo_tool": "reverse_payment",
                    "undo_param": "payment_id",
                })

        # 费用
        if not operation_type or operation_type == "expense":
            exps = db.query(models.Expense).filter(
                models.Expense.account_id == aid,
                models.Expense.is_reversed == False,
            ).order_by(models.Expense.id.desc()).limit(limit).all()
            for e in exps:
                amt = float(e.amount_l3 or 0) if hasattr(e, "amount_l3") else float(e.amount or 0)
                exp_date = getattr(e, "expense_date_l1", None) or getattr(e, "expense_date", None)
                results.append({
                    "type": "expense",
                    "id": e.id,
                    "amount": amt,
                    "category": e.category,
                    "date": exp_date.isoformat() if exp_date else None,
                    "can_undo": True,
                    "undo_tool": "reverse_expense",
                    "undo_param": "expense_id",
                })

        # 按 id 倒序合并 (id 越大越新)
        results.sort(key=lambda x: x["id"], reverse=True)
        return results[:limit]

    return {"ok": True, "operations": tool_dispatcher.run_readonly(_query)}


def undo_last_operation(arguments: dict) -> dict:
    """撤销最近一笔写操作 (自动判断类型并调对应 reverse tool)。

    用户说「撤销刚才那笔」「录错了想撤销」时用。
    先 list_recent_operations 取最近一笔, 再调对应 reverse tool。
    """
    dry_run = bool(arguments.get("dry_run", False))

    # 先查最近一笔
    recent = list_recent_operations({"limit": 1})
    ops = recent.get("operations", [])
    if not ops:
        raise BusinessError(code=None, message="没有可撤销的最近操作")

    target = ops[0]
    if dry_run:
        return _make_dry_run_result(
            operation="undo_last_operation",
            extra={
                "target": target,
                "warnings": ["dry_run 未实际撤销。确认后重调 dry_run=False 执行。"],
            },
            accounting_hint=f"将调用 {target['undo_tool']}({target['undo_param']}={target['id']}) 撤销。",
        )

    # 调对应 reverse tool
    undo_tool = target["undo_tool"]
    undo_param = target["undo_param"]
    handler = TOOL_HANDLERS.get(undo_tool)
    if not handler:
        raise BusinessError(code=None, message=f"找不到 undo tool: {undo_tool}")

    return handler({undo_param: target["id"], "reason": "undo_last_operation 自动撤销"})


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
        "description": "列出当前账本所有商品 (含 track_inventory 标志)。支持 name_like 模糊搜索。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name_like": {"type": "string", "description": "名称模糊匹配 (如 '服务' 匹配 '信息系统服务')"},
            },
        },
    },
    {
        "name": "list_customers",
        "description": "列出当前账本所有客户。支持 name_like 模糊搜索。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name_like": {"type": "string", "description": "名称模糊匹配 (如 '联通' 匹配 '中国联通宜宾分公司')"},
            },
        },
    },
    {
        "name": "list_suppliers",
        "description": "列出当前账本所有供应商。支持 name_like 模糊搜索。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name_like": {"type": "string", "description": "名称模糊匹配"},
            },
        },
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
            "用户说「我卖了一笔货」「开张销售单」「录入销售」时用本 tool。"
            "发票驱动: 先创建销项发票, 自动生成销售单。"
            "agent 只需传含税单价和税率, server 自动算不含税金额和税额。"
            "返回: invoice_id, sale_order_id, amount_with_tax, tax_amount, accounting_hint。"
            "必填参数来源: customer_name 从 list_customers 查, product_id 从 list_products 查。"
            "用户不确定时传 dry_run=True 可预演金额和会计影响, 不写库。"
            "会计影响: 借:应收账款 贷:主营业务收入+销项税额; "
            "实物商品还会 借:主营业务成本 贷:库存商品 (按 unit_cost 加权平均); 服务类商品不结转成本。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "客户名称 (从 list_customers 查)"},
                "sale_date": {"type": "string", "description": "YYYY-MM-DD"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer", "description": "商品 ID (从 list_products 查)"},
                            "quantity": {"type": "number", "description": "数量"},
                            "unit_price": {"type": "number", "description": "含税单价"},
                            "tax_rate": {"type": "number", "description": "税率数字 (如 0.01 / 0.06 / 0.13), 用户说 6% 传 0.06"},
                            "notes": {"type": "string"},
                        },
                    },
                },
                "invoice_type": {"type": "string", "default": "ordinary", "description": "ordinary 普票 / special 专票"},
                "notes": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False, "description": "True 仅预演金额, 不写库"},
            },
            "required": ["customer_name", "sale_date", "items"],
        },
    },
    {
        "name": "create_receipt",
        "description": (
            "用户说「客户付款了」「收到了款」「录入收款」时用本 tool。"
            "银行流入: 借:银行存款 贷:应收账款。"
            "必填参数 sale_order_id: 之前 create_sale_order_with_invoice 返回的, 或从 get_sale_order 查。"
            "必填参数 bank_account_id: 从 list_bank_accounts 查, 不传默认取首个。"
            "支持 dry_run 预演。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sale_order_id": {"type": "integer", "description": "关联销售单 ID"},
                "amount": {"type": "number", "description": "收款金额"},
                "payment_date": {"type": "string", "description": "YYYY-MM-DD"},
                "bank_account_id": {"type": "integer", "description": "银行账户 ID (从 list_bank_accounts 查)"},
                "description": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["sale_order_id", "amount", "payment_date"],
        },
    },
    {
        "name": "create_payment",
        "description": (
            "用户说「付了供应商款」「付钱」「发工资」「缴税」时用本 tool。"
            "银行流出: 借:应付账款/应付职工薪酬/应交税费 贷:银行存款。"
            "payment_type=expense 付费用 (related_entity_type=expense); "
            "payment_type=purchase 付采购款 (related_entity_type=purchase_order); "
            "payment_type=salary 发工资 (related_entity_type=expense, 可带 withholding_tax_amount 代扣个税); "
            "payment_type=tax 缴税 (related_entity_type=tax_payable)。"
            "必填参数 bank_account_id: 从 list_bank_accounts 查, 不传默认取首个。"
            "支持 dry_run 预演。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_type": {
                    "type": "string",
                    "enum": ["expense", "purchase", "salary", "tax"],
                    "description": "expense 付费用 / purchase 付采购 / salary 发工资 / tax 缴税",
                },
                "related_entity_type": {
                    "type": "string",
                    "description": "关联实体类型: expense / purchase_order / tax_payable",
                },
                "related_entity_id": {"type": "integer", "description": "关联实体 ID"},
                "amount": {"type": "number", "description": "付款金额 (实发, >0)"},
                "payment_date": {"type": "string", "description": "YYYY-MM-DD"},
                "bank_account_id": {"type": "integer", "description": "银行账户 ID (从 list_bank_accounts 查)"},
                "withholding_tax_amount": {
                    "type": "number",
                    "default": 0,
                    "description": "代扣个税 (仅 payment_type=salary 可用, 实发=amount, 应发=amount+withholding_tax_amount)",
                },
                "description": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["payment_type", "related_entity_type", "related_entity_id", "amount", "payment_date"],
        },
    },
    # ── 4. 采购 ──
    {
        "name": "create_purchase_order_with_invoice",
        "description": (
            "用户说「我进了一批货」「采购」「录入采购单」时用本 tool。"
            "发票驱动: 先创建进项发票, 自动生成采购单。"
            "会计影响: 借:库存商品+进项税额 贷:应付账款。"
            "小规模纳税人进项税不可抵扣, 含税全额入库存成本。"
            "必填参数 supplier_name 从 list_suppliers 查, product_id 从 list_products 查。"
            "支持 dry_run 预演。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier_name": {"type": "string", "description": "供应商名称 (从 list_suppliers 查)"},
                "purchase_date": {"type": "string", "description": "YYYY-MM-DD"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "integer", "description": "商品 ID"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number", "description": "含税单价"},
                            "tax_rate": {"type": "number", "description": "税率数字, 用户说 13% 传 0.13"},
                            "notes": {"type": "string"},
                        },
                    },
                },
                "invoice_type": {"type": "string", "default": "ordinary"},
                "notes": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["supplier_name", "purchase_date", "items"],
        },
    },
    # ── 5. 费用 ──
    {
        "name": "create_expense",
        "description": (
            "用户说「付了房租」「水电费」「工资」「录入费用」时用本 tool。"
            "会计影响: 借:管理费用 贷:应付账款 (公司付款) / 其他应付款 (个人垫付)。"
            "铁律: 已过账费用禁止删除, 必须通过 reverse_expense 冲红。"
            "支持 dry_run 预演。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["房租", "水电", "工资", "材料", "办公用品", "运费", "维修", "税金及附加", "所得税", "其他"]},
                "amount": {"type": "number"},
                "expense_date": {"type": "string", "description": "YYYY-MM-DD"},
                "description": {"type": "string"},
                "functional_category": {"type": "string", "enum": ["管理费用", "销售费用", "财务费用"], "default": "管理费用"},
                "payment_method": {"type": "string", "enum": ["company", "private_advance"], "default": "company", "description": "company 公司付款 / private_advance 个人垫付"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["category", "amount", "expense_date"],
        },
    },
    # ── 6. 银行 ──
    {
        "name": "create_bank_entry",
        "description": (
            "用户说「银行扣了手续费」「收到利息」「银行流水」时用本 tool。"
            "bank_fee: 借:财务费用 贷:银行存款 (银行扣款); "
            "interest_income: 借:银行存款 贷:财务费用 (利息收入, 冲减财务费用, 不进营业外收入)。"
            "支持 dry_run 预演。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_type": {"type": "string", "enum": ["bank_fee", "interest_income"], "description": "bank_fee 银行扣款 / interest_income 利息收入"},
                "amount": {"type": "number"},
                "transaction_date": {"type": "string", "description": "YYYY-MM-DD"},
                "description": {"type": "string"},
                "bank_account_id": {"type": "integer"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["entry_type", "amount", "transaction_date"],
        },
    },
    # ── 7. 固定资产 ──
    {
        "name": "create_fixed_asset",
        "description": (
            "用户说「买了一台电脑」「录入固定资产」「设备入账」时用本 tool。"
            "会计影响: 借:固定资产 贷:应付账款。"
            "次月起按月计提折旧: 借:管理费用 贷:累计折旧 (每月金额 = 原值×(1-残值率)÷使用寿命)。"
            "支持 dry_run 预演 (会返回 monthly_depreciation 字段)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "资产名称"},
                "cost": {"type": "number", "description": "原值"},
                "purchase_date": {"type": "string", "description": "YYYY-MM-DD"},
                "useful_life": {"type": "integer", "default": 60, "description": "使用寿命(月), 电脑默认 60"},
                "salvage_rate": {"type": "number", "default": 0.05, "description": "残值率 5%"},
                "category": {"type": "string", "default": "电子设备"},
                "notes": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["name", "cost", "purchase_date"],
        },
    },
    {
        "name": "batch_depreciate",
        "description": (
            "用户说「计提折旧」「本月折旧」时用本 tool。月结第 1 步会自动调用。"
            "会计影响: 借:管理费用/销售费用 贷:累计折旧。"
            "已月结月份禁止重复折旧。支持 dry_run 预演 (返回哪些资产会折旧+每月折旧金额)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "YYYY-MM"},
                "dry_run": {"type": "boolean", "default": False, "description": "True 返回折旧预览, 不写库"},
            },
            "required": ["period"],
        },
    },
    # ── 8. 税务申报 ──
    {
        "name": "declare_vat",
        "description": (
            "用户说「申报增值税」「报税」「交 VAT」时用本 tool。"
            "申报金额 = 发票汇总税额 (销项-进项), 不是 agent 自己算。"
            "期间格式: 小规模 YYYY-QQ (按季, 如 2026-Q2) / 一般纳税人 YYYY-MM (按月, 如 2026-06)。"
            "重复申报会被拒绝 (同 period 只能申报一次)。"
            "支持 dry_run 预演 (会返回 existing_declaration 检查是否已申报)。"
            "小规模季度销售额 ≤30 万普票免征, 6% 减按 1% 征收 (2023-2027 政策)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "小规模 YYYY-QQ / 一般纳税人 YYYY-MM"},
                "taxpayer_type": {"type": "string", "enum": ["small_scale", "general"], "description": "空则从 Account 读取"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["period"],
        },
    },
    {
        "name": "declare_surcharge",
        "description": (
            "用户说「申报附加税」「城建税怎么交」「教育费附加」时用本 tool。"
            "重要: 附加税是 L1 用户输入, 三个金额必须由用户从税务局申报表抄录, 不是系统派生!"
            "建议先 dry_run=True 拿 suggested_amounts (公式参考值) 给用户看, 用户确认后再正式申报。"
            "重复申报会被拒绝。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "小规模 YYYY-QQ / 一般纳税人 YYYY-MM"},
                "urban_construction_tax": {"type": "number", "description": "城建税金额 (用户从税务局申报表抄录)"},
                "education_surcharge": {"type": "number", "description": "教育费附加金额"},
                "local_education_surcharge": {"type": "number", "description": "地方教育附加金额"},
                "notes": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False, "description": "True 返回 suggested_amounts 供用户参考"},
            },
            "required": ["period"],
        },
    },
    # ── 9. 月结 ──
    {
        "name": "month_end_close",
        "description": (
            "用户说「月结」「结账」「月末处理」时用本 tool。"
            "5 步自动执行: 折旧→算税→结转损益→年结(仅12月)→税务核对。"
            "危险等级: 高 (会生成大量凭证, 不可逆)。"
            "默认 require_confirm=True 会先抛 BusinessError 让 agent 问用户确认, "
            "用户确认后重传 require_confirm=False 执行。"
            "重复月结会被拒绝 (同月份只能月结一次)。"
            "支持 dry_run 预演 (检查是否已月结)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "YYYY-MM"},
                "taxpayer_type": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
                "require_confirm": {"type": "boolean", "default": True, "description": "默认 True 先确认, False 直接执行"},
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
            "用户说「那张发票作废」「红冲发票」「销售取消了」时用本 tool。"
            "红字发票冲红: 标记原发票 is_reversed=True, 生成红字发票 (金额取负)。"
            "会级联冲红关联的 expense 凭证, 但不会自动红冲关联收款! "
            "若该销售已收款, 必须先 reverse_receipt 再 reverse_invoice, 否则应收和银行存款对不上。"
            "若该发票已申报 VAT, 红冲后必须重新申报 VAT。"
            "已红冲过的发票会被拒绝, 重复红冲无效。"
            "支持 dry_run 预查原单状态和警告。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "integer", "description": "原发票 ID (从 list_invoices 查)"},
                "reason": {"type": "string", "description": "冲红原因 (记入审计日志)"},
                "dry_run": {"type": "boolean", "default": False, "description": "True 仅检查原单状态, 不实际红冲"},
            },
            "required": ["invoice_id"],
        },
    },
    {
        "name": "reverse_expense",
        "description": (
            "用户说「那笔费用录错了」「红冲费用」「费用作废」时用本 tool。"
            "已过账费用禁止直接删除, 必须通过本 tool 冲红。"
            "已红冲过的费用会被拒绝, 重复红冲无效。"
            "支持 dry_run 预查。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "expense_id": {"type": "integer"},
                "reason": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["expense_id"],
        },
    },
    {
        "name": "reverse_receipt",
        "description": (
            "用户说「那笔收款录错了」「红冲收款」「客户退款」时用本 tool。"
            "生成负数 Receipt + 反向银行流水 + 红冲凭证 + 销售单 payment_status 重置为 unpaid。"
            "已红冲过的收款会被拒绝。支持 dry_run 预查。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "receipt_id": {"type": "integer"},
                "reason": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["receipt_id"],
        },
    },
    {
        "name": "reverse_payment",
        "description": (
            "用户说「那笔付款录错了」「红冲付款」「供应商退款」时用本 tool。"
            "生成负数 Payment + 反向银行流水 + 红冲凭证 + 采购单 payment_status 重置。"
            "已红冲过的付款会被拒绝。支持 dry_run 预查。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "payment_id": {"type": "integer"},
                "reason": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
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
    # ── 14. 上下文恢复 ──
    {
        "name": "list_recent_operations",
        "description": (
            "用户说「刚才那笔」「最近录了什么」「撤销上一步」时用本 tool。"
            "列出最近 N 条写操作 (按 id 倒序), 每条返回 type/id/amount/date/can_undo/undo_tool。"
            "无副作用, 可随时调。可选 operation_type 过滤 (invoice/receipt/expense)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10, "description": "返回条数, 最大 50"},
                "operation_type": {
                    "type": "string",
                    "enum": ["invoice", "receipt", "payment", "expense"],
                    "description": "可选, 只列指定类型的操作",
                },
            },
        },
    },
    {
        "name": "undo_last_operation",
        "description": (
            "用户说「撤销刚才那笔」「录错了想撤销」时用本 tool。"
            "自动 list_recent_operations(limit=1) 取最近一笔, 调对应 reverse_* tool 撤销。"
            "建议先传 dry_run=True 预查要撤销哪笔, 用户确认后再 dry_run=False 执行。"
            "危险: 不可逆, 会生成红字凭证。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "True 时只返回 target 不实际撤销",
                },
            },
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
    "create_payment": create_payment,
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
    # P4 补全: 上下文恢复
    "list_recent_operations": list_recent_operations,
    "undo_last_operation": undo_last_operation,
}
