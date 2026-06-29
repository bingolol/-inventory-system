# schemas 包统一导出
# 所有公共 schema 类从此处导出，确保 from schemas import XXX 向后兼容

from .account import AccountOut, AccountUpdate, AccountCreate

from .common import (
    ReportOverview, PaginatedResponse, PersonalSummary,
)

from .product import ProductBase, ProductCreate, ProductUpdate, ProductOut

from .partner import (
    SupplierBase, SupplierCreate, SupplierUpdate, SupplierOut,
    CustomerBase, CustomerCreate, CustomerUpdate, CustomerOut,
)

from .order import (
    PurchaseItemCreate, PurchaseItemOut,
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderOut,
    SaleItemCreate, SaleItemOut,
    SaleOrderCreate, SaleOrderUpdate, SaleOrderOut,
    InventoryOut, InventoryAdjust,
)

from .invoice import (
    InvoiceBase, InvoiceCreate, InvoiceUpdate, InvoiceOut,
    InvoiceQuickCreate, InvoiceList, InvoiceWithFixedAssetCreate, InvoiceWithFixedAssetUpdate,
    FixedAssetBlock,
)

from .expense import ExpenseBase, ExpenseCreate, ExpenseUpdate, ExpenseOut

from .personal import (
    OperationLogOut,
    PersonalTransactionCreate, PersonalTransactionUpdate, PersonalTransactionOut,
)

from .finance import (
    OpeningBalanceBase, OpeningBalanceCreate, OpeningBalanceUpdate, OpeningBalanceOut,
    FixedAssetBase, FixedAssetCreate, FixedAssetUpdate, FixedAssetOut, FixedAssetWithInvoiceUpdate,
    IntangibleAssetBase, IntangibleAssetCreate, IntangibleAssetUpdate, IntangibleAssetOut,
    TaxReport, TaxReportMonth, IncomeTaxReport,
    VATDeclaration, IncomeTaxPrepayment, AssetDepreciationDetail,
    BalanceSheet, IncomeStatement,
    CashFlowTransactionCreate, CashFlowTransactionUpdate, CashFlowTransactionOut,
    CashFlowStatement,
)

from .inventory_adjustment import InventoryAdjustmentCreate, InventoryAdjustmentOut
from .bank import BankAccountBase, BankAccountCreate, BankAccountUpdate, BankAccountOut, BankAccountList

__all__ = [
    # account
    "AccountOut", "AccountUpdate", "AccountCreate",
    # common
    "ReportOverview", "PaginatedResponse", "PersonalSummary",
    # product
    "ProductBase", "ProductCreate", "ProductUpdate", "ProductOut",
    # partner
    "SupplierBase", "SupplierCreate", "SupplierUpdate", "SupplierOut",
    "CustomerBase", "CustomerCreate", "CustomerUpdate", "CustomerOut",
    # order
    "PurchaseItemCreate", "PurchaseItemOut",
    "PurchaseOrderCreate", "PurchaseOrderUpdate", "PurchaseOrderOut",
    "SaleItemCreate", "SaleItemOut",
    "SaleOrderCreate", "SaleOrderUpdate", "SaleOrderOut",
    "InventoryOut", "InventoryAdjust",
    # invoice
    "InvoiceBase", "InvoiceCreate", "InvoiceUpdate", "InvoiceOut",
    "InvoiceQuickCreate", "InvoiceList", "InvoiceWithFixedAssetCreate",
    "InvoiceWithFixedAssetUpdate", "FixedAssetBlock",
    # expense
    "ExpenseBase", "ExpenseCreate", "ExpenseUpdate", "ExpenseOut",
    # personal
    "OperationLogOut",
    "PersonalTransactionCreate", "PersonalTransactionUpdate", "PersonalTransactionOut",
    # finance
    "OpeningBalanceBase", "OpeningBalanceCreate", "OpeningBalanceUpdate", "OpeningBalanceOut",
    "FixedAssetBase", "FixedAssetCreate", "FixedAssetUpdate", "FixedAssetOut",
    "IntangibleAssetBase", "IntangibleAssetCreate", "IntangibleAssetUpdate", "IntangibleAssetOut",
    "TaxReport", "TaxReportMonth", "IncomeTaxReport",
    "VATDeclaration", "IncomeTaxPrepayment", "AssetDepreciationDetail",
    "BalanceSheet", "IncomeStatement",
    "CashFlowTransactionCreate", "CashFlowTransactionUpdate", "CashFlowTransactionOut",
    "CashFlowStatement",
    "InventoryAdjustmentCreate", "InventoryAdjustmentOut",
]