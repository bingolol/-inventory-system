"""crud 包：按领域拆分的 CRUD 操作，统一 re-export 保持 crud.xxx 调用方式不变"""

from .base import (
    _generate_order_no, _log, get_or_create_inventory,
    list_accounts, get_account, update_account, create_account, delete_account,
)
from .products import (
    list_products, get_product, create_product, update_product, delete_product,
    list_inventory, adjust_inventory, get_stock_alerts,
)
from .partners import (
    list_suppliers, get_supplier, create_supplier, update_supplier, delete_supplier,
    list_customers, get_customer, create_customer, update_customer, delete_customer,
)
from .orders import (
    list_purchase_orders, get_purchase_order,
    list_sale_orders, get_sale_order,
    _distribute_total_price,
)
from .invoices import (
    list_invoices, get_invoice, create_invoice, update_invoice, delete_invoice,
    get_tax_report,
)
from .personal import (
    list_personal_transactions, create_personal_transaction, update_personal_transaction,
    delete_personal_transaction, get_personal_summary,
    get_personal_category_summary, get_personal_monthly_summary,
)
from .finance import (
    create_opening_balance, get_opening_balance, get_opening_balance_by_date,
    list_opening_balances, update_opening_balance, delete_opening_balance,
    get_latest_opening_balance, generate_balance_sheet, generate_income_statement,
    create_cash_flow_transaction, list_cash_flow_transactions,
    update_cash_flow_transaction, delete_cash_flow_transaction,
    generate_cash_flow_statement,
    create_fixed_asset, get_fixed_asset, list_fixed_assets, update_fixed_asset, delete_fixed_asset,
    create_intangible_asset, get_intangible_asset, list_intangible_assets, update_intangible_asset, delete_intangible_asset,
    generate_vat_declaration, generate_income_tax_prepayment, generate_asset_depreciation_detail,
)
from .logs import list_operation_logs
from .reports import get_overview, get_purchase_report, get_sale_report, get_profit_report, get_trend