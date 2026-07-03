"""commands — 命令模式包"""

from .base import Command, CommandHandler, register, dispatch, get_registered_commands

# 导入各命令模块以触发 @register 装饰器注册
from . import sale_commands  # noqa: F401
from . import purchase_commands  # noqa: F401
from . import finance_commands  # noqa: F401
from . import invoice_commands  # noqa: F401
from . import product_commands  # noqa: F401
from . import partner_commands  # noqa: F401
from . import personal_commands  # noqa: F401
from . import month_end  # noqa: F401
from . import bank_reconcile  # noqa: F401
from . import cash_commands  # noqa: F401
from . import personal_advance_commands  # noqa: F401
from . import bank_commands  # noqa: F401
from . import fixed_asset_commands  # noqa: F401

# 从子模块导出具体命令类
from .product_commands import (
    CreateProduct,
    UpdateProduct,
    DeleteProduct,
    AdjustInventory,
)
from .partner_commands import (
    CreatePartner,
    UpdatePartner,
    DeletePartner,
)
from .personal_commands import (
    CreatePersonalTransaction,
    UpdatePersonalTransaction,
    DeletePersonalTransaction,
)
from .month_end import (
    MonthEndClose,
)
from .bank_reconcile import (
    ImportBankStatement,
    ReconcileBank,
    ForceMatchBankReconciliation,
    ConfirmBankReconciliation,
    GenerateReconciliationEntry,
)
from .cash_commands import (
    CreateExpense,
    UpdateExpense,
    ReverseExpense,
    DeleteExpense,
    CreatePayment,
    ReversePayment,
    CreateReceipt,
    ReverseReceipt,
)
from .personal_advance_commands import (
    CreatePersonalAdvance,
    RepayPersonalAdvance,
    ReversePersonalAdvance,
    ReversePersonalAdvanceRepayment,
)
from .bank_commands import (
    CreateBankAccount,
    UpdateBankAccount,
    DeleteBankAccount,
    CreateBankTransaction,
    CreateBankEntry,
)
from .fixed_asset_commands import (
    DepreciateFixedAsset,
    BatchDepreciateFixedAssets,
    DisposeFixedAsset,
)

__all__ = [
    "Command",
    "CommandHandler",
    "register",
    "dispatch",
    "get_registered_commands",
    # Product commands
    "CreateProduct",
    "UpdateProduct",
    "DeleteProduct",
    "AdjustInventory",
    # Partner commands
    "CreatePartner",
    "UpdatePartner",
    "DeletePartner",
    # Personal transaction commands
    "CreatePersonalTransaction",
    "UpdatePersonalTransaction",
    "DeletePersonalTransaction",
    # Finance commands
    "CreateOpeningBalance",
    "UpdateOpeningBalance",
    # Month-end close
    "MonthEndClose",
    # Bank reconciliation
    "ImportBankStatement",
    "ReconcileBank",
    "ForceMatchBankReconciliation",
    "ConfirmBankReconciliation",
    # Cash commands
    "CreateExpense",
    "UpdateExpense",
    "ReverseExpense",
    "DeleteExpense",
    "CreatePayment",
    "ReversePayment",
    "CreateReceipt",
    "ReverseReceipt",
    # Personal advance commands
    "CreatePersonalAdvance",
    "RepayPersonalAdvance",
    "ReversePersonalAdvance",
    "ReversePersonalAdvanceRepayment",
    # Bank commands
    "CreateBankAccount",
    "UpdateBankAccount",
    "DeleteBankAccount",
    "CreateBankTransaction",
    "CreateBankEntry",
    # Fixed asset commands
    "DepreciateFixedAsset",
    "BatchDepreciateFixedAssets",
    "DisposeFixedAsset",
]