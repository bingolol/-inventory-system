"""固定资产 Command + Handler

原 routers/fixed_assets.py 中直接调用 FixedAssetEngine 的折旧/处置端点下沉到本模块，
router 只负责 HTTP 解析 + dispatch。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from commands.base import Command, CommandHandler, register
from engine_fixed_asset import FixedAssetEngine
from errors import BusinessError, ErrorCode


# ═══════════════════════════════════════════════════════════
# 1. DepreciateFixedAsset — 计提单个固定资产折旧
# ═══════════════════════════════════════════════════════════

@dataclass
class DepreciateFixedAsset(Command):
    asset_id: int = 0
    period: str = ""           # YYYY-MM


@register(DepreciateFixedAsset)
class DepreciateFixedAssetHandler(CommandHandler):
    # FixedAssetDepreciation / FixedAsset 字段由 FixedAssetEngine 写入，
    # 已在 engine_fixed_asset.py 声明；Handler 仅做编排，不再重复声明。
    def handle(self, cmd: DepreciateFixedAsset, db: Any) -> Any:
        eng = FixedAssetEngine(db, cmd.account_id)
        dep = eng.record_depreciation(cmd.asset_id, cmd.period)
        if dep is None:
            return {"message": "无需计提（已提足或不在计提期）", "depreciation_id": None}
        return {
            "message": f"折旧计提成功: {dep.amount}",
            "depreciation_id": dep.id,
            "amount": str(dep.amount),
        }


# ═══════════════════════════════════════════════════════════
# 2. BatchDepreciateFixedAssets — 批量计提折旧
# ═══════════════════════════════════════════════════════════

@dataclass
class BatchDepreciateFixedAssets(Command):
    period: str = ""           # YYYY-MM


@register(BatchDepreciateFixedAssets)
class BatchDepreciateFixedAssetsHandler(CommandHandler):
    # 批量折旧委托 FixedAssetEngine.batch_depreciate 写入，引擎已声明 @writes。
    def handle(self, cmd: BatchDepreciateFixedAssets, db: Any) -> Any:
        eng = FixedAssetEngine(db, cmd.account_id)
        results = eng.batch_depreciate(cmd.period)
        return {
            "message": f"批量折旧完成: {len(results)}项资产已计提",
            "count": len(results),
            "details": [
                {"asset_id": d.asset_id, "period": d.period, "amount": str(d.amount)}
                for d in results
            ],
        }


# ═══════════════════════════════════════════════════════════
# 3. DisposeFixedAsset — 处置固定资产
# ═══════════════════════════════════════════════════════════

@dataclass
class DisposeFixedAsset(Command):
    asset_id: int = 0
    disposal_price: Decimal = Decimal("0")
    disposal_date: str = ""            # YYYY-MM-DD
    bank_account_id: Optional[int] = None


@register(DisposeFixedAsset)
class DisposeFixedAssetHandler(CommandHandler):
    # 处置字段由 FixedAssetEngine.record_disposal 写入，引擎已声明 @writes。
    def handle(self, cmd: DisposeFixedAsset, db: Any) -> Any:
        parsed_date = None
        if cmd.disposal_date:
            try:
                parsed_date = datetime.strptime(cmd.disposal_date, "%Y-%m-%d").date()
            except ValueError:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"disposal_date 格式错误: {cmd.disposal_date}，应为 YYYY-MM-DD"
                )

        eng = FixedAssetEngine(db, cmd.account_id)
        eng.record_disposal(
            cmd.asset_id,
            cmd.disposal_price,
            disposal_date=parsed_date,
            bank_account_id=cmd.bank_account_id,
        )
        return {"message": "固定资产已处置"}
