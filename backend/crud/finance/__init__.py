"""财务 crud 包：期初余额 / 报表 / 资产 / 税务 / 收付款

re-export 全部公开函数，保持 `from crud.finance import X` 和 `crud.finance.X` 兼容。
原 crud/finance.py (1081行) 已拆分为本包下的 9 个子模块。
"""

from .opening_balances import (
    get_opening_balance,
    get_opening_balance_by_date,
    list_opening_balances,
    delete_opening_balance,
    get_latest_opening_balance,
)
from .balance_sheet import generate_balance_sheet
from .income_statement import generate_income_statement
from .cash_flow import (
    list_cash_flow_transactions,
    generate_cash_flow_statement,
)
from .cwbb_xqykjzz import generate_cwbb_xqykjzz
from .cwbb_xqykjzz_export import export_cwbb_xqykjzz
from .fixed_assets import (
    create_fixed_asset,
    get_fixed_asset,
    list_fixed_assets,
    update_fixed_asset,
    delete_fixed_asset,
)
from .intangible_assets import (
    create_intangible_asset,
    get_intangible_asset,
    list_intangible_assets,
    update_intangible_asset,
    delete_intangible_asset,
)
from .tax_declarations import (
    aggregate_vat_invoices,
    generate_vat_declaration,
    generate_income_tax_prepayment,
    generate_asset_depreciation_detail,
)
from .payments import (
    list_payments,
    get_payment,
    list_receipts,
    get_receipt,
)

__all__ = [
    # 期初余额
    "get_opening_balance",
    "get_opening_balance_by_date",
    "list_opening_balances",
    "delete_opening_balance",
    "get_latest_opening_balance",
    # 报表
    "generate_balance_sheet",
    "generate_income_statement",
    "generate_cash_flow_statement",
    "list_cash_flow_transactions",
    "generate_cwbb_xqykjzz",
    "export_cwbb_xqykjzz",
    # 固定资产
    "create_fixed_asset",
    "get_fixed_asset",
    "list_fixed_assets",
    "update_fixed_asset",
    "delete_fixed_asset",
    # 无形资产
    "create_intangible_asset",
    "get_intangible_asset",
    "list_intangible_assets",
    "update_intangible_asset",
    "delete_intangible_asset",
    # 税务
    "aggregate_vat_invoices",
    "generate_vat_declaration",
    "generate_income_tax_prepayment",
    "generate_asset_depreciation_detail",
    # 收付款
    "list_payments",
    "get_payment",
    "list_receipts",
    "get_receipt",
]
