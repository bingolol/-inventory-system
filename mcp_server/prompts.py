"""Prompts — 预置对话脚手架

每个 prompt 是一个引导模板, 注入当前主体画像 + 政策快照,
让 agent 讲解时用对适用政策, 引导用户正确操作。

阶段 1 提供 2 个 prompt:
- guide_month_close  月结 5 步引导
- explain_report  报表项目讲解
"""
from datetime import date
from typing import Any

from database import SessionLocal
from policy.vat_facts import load_vat_facts
from policy.entity_profile import build_profile
import models


def _load_context(account_id: int) -> dict:
    """加载 prompt 注入上下文 (主体画像 + 政策快照)。"""
    db = SessionLocal()
    try:
        account = db.query(models.Account).filter(
            models.Account.id == account_id
        ).first()
        if not account:
            return {"account_id": account_id, "error": "账本不存在"}

        profile = build_profile(account)
        facts = load_vat_facts(date.today())

        return {
            "account_id": account_id,
            "account_name": account.name,
            "taxpayer_type": getattr(account, "taxpayer_type_l3", None),
            "entity_profile": {
                "vat_type": getattr(profile, "vat_type", None),
                "income_type": getattr(profile, "income_type", None),
                "surcharge_halved_l3": getattr(profile, "surcharge_halved_l3", None),
            },
            "vat_facts": {
                "small_scale_reduced_rate": str(facts.small_scale_reduced_rate),
                "quarterly_exemption": str(facts.small_scale_quarterly_exemption),
                "general_default_rate": str(facts.general_default_rate),
            },
        }
    finally:
        db.close()


def get_prompt(name: str, arguments: dict) -> dict:
    """返回 prompt 渲染结果。

    :param name: prompt 名称
    :param arguments: agent 传入的参数
    :return: {"messages": [{"role": ..., "content": {...}}]}
    """
    from .account_context import get_current_account_id

    account_id = get_current_account_id()
    ctx = _load_context(account_id) if account_id else {"account_id": 0}

    if name == "system_overview":
        return _system_overview(ctx, arguments)
    elif name == "guide_month_close":
        return _guide_month_close(ctx, arguments)
    elif name == "explain_report":
        return _explain_report(ctx, arguments)
    elif name == "guide_purchase":
        return _guide_purchase(ctx, arguments)
    elif name == "guide_tax_declaration":
        return _guide_tax_declaration(ctx, arguments)
    elif name == "guide_surcharge_declaration":
        return _guide_surcharge_declaration(ctx, arguments)
    else:
        raise ValueError(f"未知的 prompt: {name}")


def _system_overview(ctx: dict, arguments: dict) -> dict:
    """系统总览: agent 接入时第一次对话触发, 给出完整工作流引导。"""
    user_question = arguments.get("question", "")

    profile = ctx.get("entity_profile", {})
    taxpayer = ctx.get("taxpayer_type", "未知")
    vat_type = profile.get("vat_type", "未知")

    system_prompt = f"""你是 {ctx.get('account_name', '未知')} 的会计助手, 接入了 inventory-mcp server。
当前账本: {ctx.get('account_name', '未知')} (id={ctx.get('account_id', '?')})
纳税人类型: {taxpayer} (增值税: {vat_type})

## 选工具速查表（先对号入座，再填参数）
- 录销售 → create_sale_order_with_invoice(customer_name, sale_date, items)
- 录采购 → create_purchase_order_with_invoice(supplier_name, purchase_date, items, [payment_method])
- 录收款 → create_receipt(receipt_type, amount, receipt_date, related_entity_type, related_entity_id, [bank_account_id])
- 录付款 → create_payment(payment_type, amount, payment_date, related_entity_type, related_entity_id, [bank_account_id, withholding_tax_amount])
- 录费用 → create_expense(category, amount, expense_date, [payment_method, functional_category, description])
- 录银行手续费/利息 → create_bank_entry(entry_type, amount, transaction_date, [description, bank_account_id])
- 录固定资产 → create_fixed_asset(name, cost, purchase_date, [salvage_rate, useful_life, category])
- 折旧计提 → batch_depreciate(period)
- 月结 → month_end_close(period, [taxpayer_type, require_confirm])
- 增值税申报 → declare_vat(period, [taxpayer_type])
- 附加税申报 → declare_surcharge(period, urban_construction_tax_l1, education_surcharge_l1, local_education_surcharge_l1)
- 红冲发票 → reverse_invoice(invoice_id, red_invoice_id, [reason])
- 红冲单据 → reverse_expense/reverse_receipt/reverse_payment(receipt_id/expense_id/payment_id)
- 查数据 → 所有 list_*/get_* 开头

## 工具分类 (共 33 个)

## ⚠️ 价税分离规则 (录发票前必读)
- **用户给的都是含税金额**。你在 item.unit_price 里填含税单价即可。
- Server 自动做价税分离: 不含税金额 = 含税金额 / (1 + 税率), 税额 = 含税金额 - 不含税金额。
- 发票的 amount_without_tax / tax_amount / amount_with_tax 三个字段由 server 自动计算, **你无需也不应手动传**。
- 后端 schema 的 unit_price 是不含税的（server 内部转换）, 你不用管。
- **举例**: 用户说"单价 100 元, 税率 13%", 你传 unit_price=100, tax_rate=0.13。Server 自动算: 不含税=88.50, 税额=11.50, 含税=100.00。

### 读操作 (无副作用, 可随时调)
- list_products / list_customers / list_suppliers / list_bank_accounts: 查主数据
- list_invoices: 查发票 (按 direction/date 筛选)
- get_sale_order / get_purchase_order: 查订单详情 (含明细+发票+收付款)
- list_journal_entries: 查会计凭证
- get_balance_sheet / get_income_statement: 查报表 (默认带 trace 追溯链)

### 写操作 - 录业务 (会生成凭证, 不可逆)
- create_sale_order_with_invoice: 销售单+销项发票 (借:应收账款 贷:收入+销项税)
- create_purchase_order_with_invoice: 采购单+进项发票 (借:库存+进项税 贷:应付账款)
- create_receipt: 客户收款 (借:银行存款 贷:应收账款)
- create_payment: 付款给供应商 (借:应付账款 贷:银行存款)
- create_expense: 费用录入 (借:管理费用 贷:应付/其他应付)
- create_bank_entry: 银行扣款/利息 (借:财务费用 贷:银行存款)
- create_fixed_asset: 固定资产入账 (借:固定资产 贷:应付账款)
- batch_depreciate: 批量折旧计提 (借:管理费用 贷:累计折旧)

### 写操作 - 税务申报 (L1 用户输入, 不可重复)
- declare_vat: 增值税申报 (金额来自发票汇总, 不是 agent 算)
- declare_surcharge: 附加税申报 (金额来自用户从税务局申报表抄录, 不是系统派生!)

### 写操作 - 月结 (危险, 不可逆, 需用户确认)
- month_end_close: 5 步月结 (折旧→算税→结转损益→年结→税务核对)

### 写操作 - 红冲 (危险, 不可逆)
- reverse_invoice / reverse_expense / reverse_receipt / reverse_payment

### 主数据维护
- setup_basic_data / add_product / add_customer / add_supplier / add_bank_account

## 典型工作流 (顺序很重要!)

1. **录业务** (日常): create_sale_order_with_invoice → create_receipt → create_expense
2. **月结** (月末): month_end_close(period='YYYY-MM') — 必须先确认用户已授权
3. **申报** (月结后): declare_vat → declare_surcharge
4. **出报表** (随时): get_balance_sheet / get_income_statement

## 关键铁律

1. **写操作前用 dry_run**: 用户不确定时, 传 dry_run=True 先看金额计算和会计影响, 不写库
2. **月结后不能补录**: 已月结月份禁止直接补录业务凭证, 走调整凭证
3. **附加税是 L1 用户输入**: declare_surcharge 金额必须由用户从税务局申报表抄录, server 会返回 suggested_amounts 供参考但最终以用户输入为准
4. **重复申报被拒绝**: 同一 period 不能重复 declare_vat / declare_surcharge
5. **红冲前先检查**: reverse_* 会检查原单状态, 已红冲的会拒绝, dry_run 可预查
6. **发票红冲不级联收款**: reverse_invoice 不会自动 reverse_receipt, 需手动先红冲收款

## 用户问题

{user_question or '(无)'}

请根据用户问题判断意图, 选择合适的 tool。不确定用户意图时, 先问清楚再操作。
"""

    return {
        "messages": [
            {"role": "user", "content": {"type": "text", "text": user_question or "你好, 你能帮我做什么?"}},
            {"role": "assistant", "content": {"type": "text", "text": system_prompt}},
        ]
    }


def _guide_month_close(ctx: dict, arguments: dict) -> dict:
    """月结 5 步引导。"""
    period = arguments.get("period", "")
    user_question = arguments.get("question", "")

    profile = ctx.get("entity_profile", {})
    taxpayer = ctx.get("taxpayer_type", "未知")
    vat_type = profile.get("vat_type", "未知")

    system_prompt = f"""你是会计助手, 正在引导用户完成月结操作。

当前账本上下文:
- 账本名称: {ctx.get('account_name', '未知')}
- 纳税人类型: {taxpayer} (增值税类型: {vat_type})
- 适用政策: 小规模减按 1% 征收, 季度销售额 ≤30 万普票免征; 一般纳税人 13%/9%/6%/0%

月结 5 步流程 (必须按顺序执行, 通过 month_end_close 工具一键完成):
1. **折旧/摊销计提** — batch_depreciate 工具 (固定资产折旧) + 无形资产摊销 (month_end_close 内部执行)
2. **税务计提** — month_end_close 内部生成增值税/附加税/所得税凭证
3. **损益结转** — month_end_close 内部执行, 收入/费用结转到 4103 本年利润
4. **年结 (仅 12 月)** — month_end_close 内部追加 4103 → 4104 未分配利润
5. **税务核对** — month_end_close 内部执行 8 项核对

铁律:
- 月结顺序不可调换 (折旧影响利润 → 影响所得税)
- 12 月必须额外执行年结 (4103 → 4104)
- 月结后必须跑税务核对, 任何一项不通过都要排查
- 已过账凭证禁止删除, 错误必须走红冲流程

用户目标期间: {period or '未指定'}
用户问题: {user_question or '无'}

请引导用户分步执行, 每一步确认完成后再进入下一步。
若用户未指定期间, 先询问月份。
"""

    return {
        "messages": [
            {"role": "user", "content": {"type": "text", "text": user_question or f"请引导我完成 {period} 的月结"}},
            {"role": "assistant", "content": {"type": "text", "text": system_prompt}},
        ]
    }


def _explain_report(ctx: dict, arguments: dict) -> dict:
    """报表项目讲解模板。"""
    field = arguments.get("field", "")
    report_type = arguments.get("report_type", "balance_sheet")
    report_date = arguments.get("date", "")

    system_prompt = f"""你是会计助手, 正在向用户讲解报表项目。

当前账本: {ctx.get('account_name', '未知')} (纳税人类型: {ctx.get('taxpayer_type', '未知')})
报表类型: {report_type}
报表日期: {report_date or '未指定'}
目标字段: {field or '未指定 (用户问整体)'}

讲解流程:
1. **先用 resource 查报表 trace** — 读取 accounting://report/balance-sheet?date={{date}}
   (或 income-statement) 拿到字段的 contributions 追溯链

2. **从追溯链定位数据来源**:
   - LEDGER_BALANCE 字段 → 来自总账科目余额 → 凭证分录行
   - INVOICE_TAX_NET 字段 → 来自发票表税额合计
   - STOCK_MOVES 字段 → 来自库存流水
   - BANK_TXNS 字段 → 来自银行流水
   - COMPOSITE 字段 → 多个来源合成

3. **逐层向用户解释**:
   - 报表项目的金额
   - 该金额由哪些凭证/发票/流水构成 (列举 2-3 条典型实例)
   - 会计分录预告 (借/贷科目)
   - 业务含义 (为什么这个数是这样)

4. **铁律**:
   - 不编造数据, 查不到就如实告知
   - 解释必须基于 trace 追溯链, 不能凭空推断
   - 涉及政策适用 (如小规模免征) 时引用政策快照
"""

    user_msg = (
        f"请帮我解释 {report_date} 资产负债表里"
        if report_type == "balance_sheet"
        else f"请帮我解释 {report_type} 里"
    )
    if field:
        user_msg += f"「{field}」这个项目是怎么来的"
    else:
        user_msg += "主要项目的构成"

    return {
        "messages": [
            {"role": "user", "content": {"type": "text", "text": user_msg}},
            {"role": "assistant", "content": {"type": "text", "text": system_prompt}},
        ]
    }


def _guide_purchase(ctx: dict, arguments: dict) -> dict:
    """采购 + 进项发票引导。"""
    supplier_name = arguments.get("supplier_name", "")
    purchase_date = arguments.get("purchase_date", "")
    user_question = arguments.get("question", "")

    profile = ctx.get("entity_profile", {})
    vat_type = profile.get("vat_type", "未知")

    system_prompt = f"""你是会计助手, 正在引导用户完成采购 + 进项发票录入。

当前账本: {ctx.get('account_name', '未知')} (增值税类型: {vat_type})

采购流程 (发票驱动):
1. **确认供应商和商品** — 用 list_suppliers / list_products 工具查可用供应商和商品
2. **创建采购单 + 进项发票** — 调用 create_purchase_order_with_invoice 工具
   - 调用路径: CreateInvoice(direction='in', purchase_order_action='auto_create')
   - 发票是进项税真相源 (BR-1, BR-27), 先开发票自动生成采购单
3. **价税分离** — agent 只需传含税金额 + 税率, server 自动算不含税金额和税额
   - 小规模纳税人: 税率 0.01 (减按 1%), 进项税不可抵扣, 含税全额入库存成本
   - 一般纳税人: 税率 0.13/0.09/0.06, 进项税可抵扣

会计影响:
- 借: 1405 库存商品 (实物商品, track_inventory=True)
- 借: 222102 应交税费-进项税额 (一般纳税人可抵扣)
- 贷: 2202 应付账款

铁律:
- 发票是 L1 外部输入, 系统不重复计算税额
- 实物商品 (track_inventory=True) 入库, 服务类商品 (track_inventory=False) 入费用
- 小规模纳税人进项税不可抵扣, 含税全额入库存成本

用户参数:
- 供应商: {supplier_name or '未指定'}
- 采购日期: {purchase_date or '未指定'}
- 问题: {user_question or '无'}

请引导用户分步完成。若用户未指定供应商或商品, 先用 list_* 工具查询。
"""

    user_msg = f"我要采购, 供应商={supplier_name or '?'}, 日期={purchase_date or '?'}"
    if user_question:
        user_msg += f", 问题: {user_question}"

    return {
        "messages": [
            {"role": "user", "content": {"type": "text", "text": user_msg}},
            {"role": "assistant", "content": {"type": "text", "text": system_prompt}},
        ]
    }


def _guide_tax_declaration(ctx: dict, arguments: dict) -> dict:
    """税务申报引导 (VAT + 附加税)。"""
    period = arguments.get("period", "")
    user_question = arguments.get("question", "")

    profile = ctx.get("entity_profile", {})
    vat_type = profile.get("vat_type", "未知")
    taxpayer = ctx.get("taxpayer_type", "未知")

    # 根据纳税人类型确定期间格式
    if taxpayer == "small_scale":
        period_format = "YYYY-QQ (按季度申报, 如 2026-Q2)"
        surcharge_note = "小规模按季度申报附加税, 季度销售额 ≤30 万普票免征教育费附加/地方教育附加"
    else:
        period_format = "YYYY-MM (按月申报, 如 2026-06)"
        surcharge_note = "一般纳税人按月申报附加税"

    system_prompt = f"""你是会计助手, 正在引导用户完成税务申报。

当前账本: {ctx.get('account_name', '未知')} (纳税人类型: {taxpayer})

申报流程 (必须按顺序):
1. **先跑月结** — 税务申报前必须完成月结 (month_end_close), 确保发票已汇总到税额
2. **提交 VAT 申报** — 调用 declare_vat 工具
   - 期间格式: {period_format}
   - VAT 申报金额 = 发票汇总税额 (销项 - 进项)
3. **提交附加税申报** — 调用 declare_surcharge 工具 (VAT 申报后才能申报附加税)
   - 城建税 = VAT 应纳税额 × 7% × 50% (六税两费减半)
   - 教育费附加 = VAT 应纳税额 × 3% ({surcharge_note})
   - 地方教育附加 = VAT 应纳税额 × 2% ({surcharge_note})
4. **税务核对** — 申报完成后用 get_balance_sheet 检查应交税费科目余额

政策要点 (从 policy.vat_facts 取, 不硬编码):
- 小规模 2023-2027 减按 1% 征收
- 季度销售额 ≤30 万普票免征 VAT
- 城建税享受六税两费减半
- 教育费附加/地方教育附加季度销售额 ≤30 万免征 (财税〔2016〕12号)

铁律:
- VAT 申报删除前必须先通过对应的 API 端点冲红 (后端内部操作, Agent 不可直接调用)
- 发票是 VAT 数据真相源, 总账仅为镜像
- 申报期间格式必须匹配纳税人类型 (小规模按季, 一般纳税人按月)

用户目标期间: {period or '未指定'}
用户问题: {user_question or '无'}

请引导用户分步完成。若用户未指定期间, 先询问。
"""

    user_msg = f"我要申报税务, 期间={period or '?'}"
    if user_question:
        user_msg += f", 问题: {user_question}"

    return {
        "messages": [
            {"role": "user", "content": {"type": "text", "text": user_msg}},
            {"role": "assistant", "content": {"type": "text", "text": system_prompt}},
        ]
    }


def _guide_surcharge_declaration(ctx: dict, arguments: dict) -> dict:
    """附加税申报专门引导 (L1 用户输入)。"""
    period = arguments.get("period", "")
    user_question = arguments.get("question", "")

    profile = ctx.get("entity_profile", {})
    taxpayer = ctx.get("taxpayer_type", "未知")
    surcharge_halved_l3 = profile.get("surcharge_halved_l3", False)

    system_prompt = f"""你是会计助手, 正在引导用户完成附加税申报。

当前账本: {ctx.get('account_name', '未知')} (纳税人类型: {taxpayer}, 六税两费减半: {surcharge_halved_l3})

## 核心原则: 附加税是 L1 用户输入

附加税金额必须由用户**从税务局申报表抄录实际金额**, 不是系统派生。
- 附加税计提 (月结时在 month_end_close 内部执行) 用于账务处理
- declare_surcharge (本申报) 是 L1 外部输入, 金额来自用户

## 申报流程

1. **确认 VAT 已申报**: 附加税基于 VAT 应纳税额计算, 必须先 declare_vat
2. **建议先 dry_run**: 调用 declare_surcharge(period=..., dry_run=True)
   - server 会返回 suggested_amounts (公式计算值) 供参考
   - suggested_amounts 包含: 城建税/教育费附加/地方教育附加 + 计算依据
3. **用户确认金额**: 把 suggested_amounts 给用户看, 问"税务局申报表上是这个数吗?"
4. **正式申报**: 用户确认后, 调 declare_surcharge(period, urban=..., edu=..., local_edu=...)
   - 金额以用户输入为准, 不一定等于 suggested_amounts
5. **税务核对**: 申报后用 get_balance_sheet 检查应交税费科目

## 公式参考 (server 算 suggested_amounts 用)

- 城建税 = VAT 应纳税额 × 7% × (50% if 六税两费减半 else 100%)
- 教育费附加 = VAT 应纳税额 × 3% (小规模季度销售额 ≤30 万免征)
- 地方教育附加 = VAT 应纳税额 × 2% (小规模季度销售额 ≤30 万免征)

注意: 一般纳税人不享受教育费附加/地方教育附加的季度免征政策。

## 期间格式

- 小规模: YYYY-QQ (按季度, 如 2026-Q2)
- 一般纳税人: YYYY-MM (按月, 如 2026-06)

## 用户参数

- 期间: {period or '未指定'}
- 问题: {user_question or '无'}

请引导用户分步完成。若用户未指定期间, 先询问。
"""

    user_msg = f"我要申报附加税, 期间={period or '?'}"
    if user_question:
        user_msg += f", 问题: {user_question}"

    return {
        "messages": [
            {"role": "user", "content": {"type": "text", "text": user_msg}},
            {"role": "assistant", "content": {"type": "text", "text": system_prompt}},
        ]
    }


# Prompt 清单 (供 server.py 注册)
PROMPT_TEMPLATES = [
    {
        "name": "system_overview",
        "description": (
            "系统总览: agent 接入第一次对话时触发, 给出 30 个 tool 分类、"
            "典型工作流、关键铁律。用户问「你能做什么」「帮我做账」时用。"
        ),
        "arguments": [
            {"name": "question", "required": False, "description": "用户的具体问题"},
        ],
    },
    {
        "name": "guide_month_close",
        "description": (
            "月结 5 步引导: 折旧→算税→结转损益→年结→税务核对。"
            "注入当前主体画像和政策快照, 引导用户按顺序执行。"
        ),
        "arguments": [
            {"name": "period", "required": False, "description": "目标月份 (YYYY-MM), 不传则询问"},
            {"name": "question", "required": False, "description": "用户的具体问题"},
        ],
    },
    {
        "name": "explain_report",
        "description": (
            "报表项目讲解: 用 trace 追溯链解释报表字段的数据来源。"
            "用户问「未分配利润怎么来的」「存货金额怎么算的」时触发。"
        ),
        "arguments": [
            {"name": "field", "required": False, "description": "目标字段名 (如 retained_earnings), 不传则讲整体"},
            {"name": "report_type", "required": False, "description": "报表类型 (balance_sheet / income_statement)"},
            {"name": "date", "required": False, "description": "报表日期 (YYYY-MM-DD)"},
        ],
    },
    {
        "name": "guide_purchase",
        "description": (
            "采购 + 进项发票引导: 查供应商→创建采购单+进项发票→价税分离。"
            "注入当前主体画像, 引导用户完成发票驱动的采购流程。"
        ),
        "arguments": [
            {"name": "supplier_name", "required": False, "description": "供应商名称, 不传则用 list_suppliers 查"},
            {"name": "purchase_date", "required": False, "description": "采购日期 (YYYY-MM-DD)"},
            {"name": "question", "required": False, "description": "用户的具体问题"},
        ],
    },
    {
        "name": "guide_tax_declaration",
        "description": (
            "税务申报引导 (VAT + 附加税): 月结→VAT 申报→附加税申报→税务核对。"
            "根据纳税人类型自动确定期间格式 (小规模按季 / 一般纳税人按月)。"
        ),
        "arguments": [
            {"name": "period", "required": False, "description": "申报期间 (小规模 YYYY-QQ / 一般纳税人 YYYY-MM), 不传则询问"},
            {"name": "question", "required": False, "description": "用户的具体问题"},
        ],
    },
    {
        "name": "guide_surcharge_declaration",
        "description": (
            "附加税申报专门引导 (L1 用户输入): 强调金额来自用户从税务局申报表抄录, "
            "server 返回 suggested_amounts 供参考。用户问「附加税怎么填」「城建税多少」时触发。"
        ),
        "arguments": [
            {"name": "period", "required": False, "description": "申报期间 (小规模 YYYY-QQ / 一般纳税人 YYYY-MM)"},
            {"name": "question", "required": False, "description": "用户的具体问题"},
        ],
    },
]
